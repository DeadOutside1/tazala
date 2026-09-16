"""
Unit tests for Tazala Analytics & Feedback system:
- User tracking, scan tracking, and clean tracking
- 1 user = 1 review deduplication logic (ratings_count not inflated)
- Average rating and summary computations
- Safe review formatting with <=150 char comment truncation
- Admin dashboard string formatting
"""
import json
from unittest.mock import AsyncMock

import pytest

from app.analytics.schemas import AnalyticsSummary, ReviewItem
from app.analytics.service import AnalyticsService


@pytest.fixture(autouse=True)
def isolate_reviews_file(tmp_path, monkeypatch):
    """Ensure all analytics tests write reviews to an isolated temporary file."""
    fake_reviews = tmp_path / "reviews.jsonl"
    monkeypatch.setattr("app.analytics.service._get_reviews_file", lambda: fake_reviews)
    return fake_reviews


@pytest.mark.asyncio
async def test_record_user():
    """Test user ID is recorded into Redis set."""
    mock_redis = AsyncMock()
    await AnalyticsService.record_user(mock_redis, 12345678)
    mock_redis.sadd.assert_called_once_with("tazala:users", "12345678")


@pytest.mark.asyncio
async def test_record_scan():
    """Test scan increment and user tracking."""
    mock_redis = AsyncMock()
    await AnalyticsService.record_scan(mock_redis, 12345678)
    mock_redis.sadd.assert_called_once_with("tazala:users", "12345678")
    mock_redis.hincrby.assert_called_once_with("tazala:metrics", "total_scans", 1)


@pytest.mark.asyncio
async def test_record_clean():
    """Test clean metrics incremented atomically."""
    mock_redis = AsyncMock()
    await AnalyticsService.record_clean(
        mock_redis,
        user_id=12345678,
        messages=150,
        folders=3,
        hours=1.2,
    )
    mock_redis.sadd.assert_called_once_with("tazala:users", "12345678")
    assert mock_redis.hincrby.call_count == 3
    mock_redis.hincrbyfloat.assert_called_once_with(
        "tazala:metrics", "time_saved_hours", 1.2
    )


@pytest.mark.asyncio
async def test_save_review_first_time():
    """Test saving a new review increments count and sum."""
    mock_redis = AsyncMock()
    mock_redis.hget.return_value = None  # No previous review

    review = await AnalyticsService.save_review(
        redis=mock_redis,
        user_id=12345,
        username="john_doe",
        rating=5,
        comment="Great bot!",
    )

    assert review.user_id == 12345
    assert review.rating == 5
    assert review.comment == "Great bot!"
    # Must increment both count and sum
    mock_redis.hincrby.assert_any_call("tazala:metrics", "ratings_count", 1)
    mock_redis.hincrby.assert_any_call("tazala:metrics", "ratings_sum", 5)


@pytest.mark.asyncio
async def test_save_review_deduplication_updates_rating():
    """
    Test 1 user = 1 review:
    If a user already reviewed with 3 stars and updates to 5 stars,
    ratings_count is NOT incremented, and ratings_sum is adjusted by +2.
    """
    mock_redis = AsyncMock()
    prev_review = {
        "user_id": 12345,
        "username": "john_doe",
        "rating": 3,
        "comment": "Old comment",
        "created_at": "2026-09-15 10:00:00 UTC",
    }
    mock_redis.hget.return_value = json.dumps(prev_review).encode()

    review = await AnalyticsService.save_review(
        redis=mock_redis,
        user_id=12345,
        username="john_doe",
        rating=5,
        comment="Updated comment!",
    )

    assert review.rating == 5
    # ratings_count must NOT be incremented
    for call in mock_redis.hincrby.call_args_list:
        assert call.args != ("tazala:metrics", "ratings_count", 1)

    # ratings_sum must be adjusted by diff (5 - 3 = 2)
    mock_redis.hincrby.assert_called_once_with("tazala:metrics", "ratings_sum", 2)


@pytest.mark.asyncio
async def test_get_summary():
    """Test summary aggregation and average rating calculation."""
    mock_redis = AsyncMock()
    mock_redis.scard.return_value = 42
    mock_redis.hgetall.return_value = {
        b"total_scans": b"100",
        b"total_cleans": b"50",
        b"messages_marked": b"12500",
        b"folders_created": b"120",
        b"time_saved_hours": b"25.5",
        b"ratings_count": b"10",
        b"ratings_sum": b"48",
    }

    summary = await AnalyticsService.get_summary(mock_redis)

    assert summary.total_users == 42
    assert summary.total_scans == 100
    assert summary.total_cleans == 50
    assert summary.messages_marked == 12500
    assert summary.folders_created == 120
    assert summary.time_saved_hours == 25.5
    assert summary.ratings_count == 10
    assert summary.avg_rating == 4.8


def test_format_dashboard():
    """Test admin dashboard formatting."""
    summary = AnalyticsSummary(
        total_users=10,
        total_scans=15,
        total_cleans=8,
        messages_marked=5000,
        folders_created=20,
        time_saved_hours=12.5,
        ratings_count=4,
        avg_rating=4.5,
    )
    formatted = AnalyticsService.format_dashboard(summary)
    assert "Tazala Admin Dashboard" in formatted
    assert "10" in formatted
    assert "5,000" in formatted
    assert "4.5 / 5.0" in formatted


def test_format_reviews_list_truncation():
    """
    Test reviews formatting safely truncates comments longer than 150 characters
    to prevent exceeding Telegram message size limits.
    """
    long_comment = "A" * 300
    reviews = [
        ReviewItem(
            user_id=1,
            username="tester",
            rating=5,
            comment=long_comment,
            created_at="2026-09-16 00:00:00 UTC",
        )
    ]
    formatted = AnalyticsService.format_reviews_list(reviews)
    assert "@tester" in formatted
    assert "⭐⭐⭐⭐⭐" in formatted
    # Truncated comment has 150 chars + "..."
    assert "A" * 150 + "..." in formatted
    assert "A" * 151 not in formatted


def test_format_reviews_list_html_escaping():
    """Test usernames and comments with HTML/special characters are safely escaped."""
    reviews = [
        ReviewItem(
            user_id=2,
            username="john_doe_99",
            rating=5,
            comment="Awesome <cool> & 'great' bot!",
            created_at="2026-09-16 00:00:00 UTC",
        )
    ]
    formatted = AnalyticsService.format_reviews_list(reviews)
    assert "@john_doe_99" in formatted
    assert "&lt;cool&gt;" in formatted
    assert "&amp;" in formatted


@pytest.mark.asyncio
async def test_get_summary_disk_fallback_deduplication(tmp_path, monkeypatch):
    """Test that disk fallback deduplicates reviews by user_id so ratings_count is accurate."""
    fake_file = tmp_path / "reviews.jsonl"
    monkeypatch.setattr("app.analytics.service._get_reviews_file", lambda: fake_file)

    line1 = '{"user_id": 999, "username": "u1", "rating": 3, "created_at": "2026-09-16"}\n'
    line2 = '{"user_id": 999, "username": "u1", "rating": 5, "created_at": "2026-09-16"}\n'
    fake_file.write_text(line1 + line2, encoding="utf-8")

    mock_redis = AsyncMock()
    mock_redis.scard.return_value = 1
    mock_redis.hgetall.return_value = {}  # Empty redis metrics

    summary = await AnalyticsService.get_summary(mock_redis)
    # Deduplication ensures count is 1 and rating is 5.0 (not count 2 and rating 4.0)
    assert summary.ratings_count == 1
    assert summary.avg_rating == 5.0


