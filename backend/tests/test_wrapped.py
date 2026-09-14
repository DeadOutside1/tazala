"""
Unit tests for the Wrapped module:
- Archetype determination & Zen Score boundaries
- Time-saved calculation
- High-res card graphic rendering (Pillow PNG verification)
- Redis caching of WrappedStats
"""
import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from app.cleaner.schemas import CleanResult
from app.scanner.schemas import ScanResult
from app.wrapped.schemas import ZenArchetype
from app.wrapped.service import WrappedService

# --- 1. Archetype and Scoring Tests ---


def test_archetype_determination_monk():
    """Test Digital Monk archetype for clean, low unread accounts."""
    now = datetime.now(UTC)
    scan = ScanResult(
        session_id="monk-1",
        scanned_at=now,
        total_dialogs=20,
        total_unread=100,
        dead_count=1,
        zombie_count=0,
        dead_percentage=5.0,
    )
    stats = WrappedService.calculate_wrapped_stats(scan, username="zen_user")

    assert stats.archetype == ZenArchetype.DIGITAL_MONK
    assert stats.archetype_title == "Цифровой монах"
    assert stats.zen_score >= 90
    assert stats.username == "zen_user"


def test_archetype_determination_collector():
    """Test Info Collector archetype for accounts with 501-5000 unreads."""
    now = datetime.now(UTC)
    scan = ScanResult(
        session_id="collector-1",
        scanned_at=now,
        total_dialogs=50,
        total_unread=1500,
        dead_count=5,
        zombie_count=2,
        dead_percentage=14.0,
    )
    stats = WrappedService.calculate_wrapped_stats(scan)

    assert stats.archetype == ZenArchetype.INFO_COLLECTOR
    assert stats.archetype_title == "Инфо-коллекционер"


def test_archetype_determination_chaos_lord():
    """Test Chaos Lord archetype for accounts with 5001-20000 unreads or >35% dead chats."""
    now = datetime.now(UTC)
    # Case A: High unread count
    scan_a = ScanResult(
        session_id="chaos-1",
        scanned_at=now,
        total_dialogs=100,
        total_unread=8000,
        dead_percentage=10.0,
    )
    stats_a = WrappedService.calculate_wrapped_stats(scan_a)
    assert stats_a.archetype == ZenArchetype.CHAOS_LORD

    # Case B: High dead chats percentage (> 35%)
    scan_b = ScanResult(
        session_id="chaos-2",
        scanned_at=now,
        total_dialogs=100,
        total_unread=200,
        dead_percentage=40.0,
    )
    stats_b = WrappedService.calculate_wrapped_stats(scan_b)
    assert stats_b.archetype == ZenArchetype.CHAOS_LORD


def test_archetype_determination_digital_hoarder():
    """Test Digital Hoarder archetype for extreme chaos (>20k unreads or >60% dead chats)."""
    now = datetime.now(UTC)
    # Case A: Massive unreads
    scan_a = ScanResult(
        session_id="hoard-1",
        scanned_at=now,
        total_dialogs=200,
        total_unread=35000,
        dead_percentage=15.0,
    )
    stats_a = WrappedService.calculate_wrapped_stats(scan_a)
    assert stats_a.archetype == ZenArchetype.DIGITAL_HOARDER

    # Case B: Extreme dead chat percentage
    scan_b = ScanResult(
        session_id="hoard-2",
        scanned_at=now,
        total_dialogs=100,
        total_unread=100,
        dead_percentage=75.0,
    )
    stats_b = WrappedService.calculate_wrapped_stats(scan_b)
    assert stats_b.archetype == ZenArchetype.DIGITAL_HOARDER


# --- 2. Time-Saved Calculation Tests ---


def test_time_saved_formula():
    """Test hours calculation: (messages * 15s) / 3600 rounded to 1 decimal."""
    now = datetime.now(UTC)

    # 1000 messages -> 15000s -> 4.166... -> 4.2h
    scan_1k = ScanResult(session_id="t-1k", scanned_at=now, total_unread=1000)
    stats_1k = WrappedService.calculate_wrapped_stats(scan_1k)
    assert stats_1k.time_saved_hours == 4.2

    # 24000 messages -> 360000s -> 100.0h
    scan_24k = ScanResult(session_id="t-24k", scanned_at=now, total_unread=24000)
    stats_24k = WrappedService.calculate_wrapped_stats(scan_24k)
    assert stats_24k.time_saved_hours == 100.0


def test_calculate_with_clean_result_override():
    """Test clean_result takes precedence over scan_result for cleared messages count."""
    now = datetime.now(UTC)
    scan = ScanResult(session_id="override", scanned_at=now, total_unread=5000)
    clean = CleanResult(
        session_id="override",
        messages_marked=4800,
        folders_created=["💼 Работа", "📰 Новости"],
        duration_seconds=12.5,
        session_destroyed=False,
    )
    stats = WrappedService.calculate_wrapped_stats(scan, clean_result=clean)
    assert stats.messages_cleared == 4800
    assert stats.folders_created_count == 2


# --- 3. Image Generation Tests ---


def test_generate_wrapped_card_png_output():
    """Test card generation outputs valid PNG with exact 1080x1350 resolution."""
    now = datetime.now(UTC)
    scan = ScanResult(
        session_id="card-test",
        scanned_at=now,
        total_dialogs=85,
        total_unread=4200,
        dead_count=12,
        zombie_count=4,
        dead_percentage=18.8,
    )
    stats = WrappedService.calculate_wrapped_stats(scan, username="telegram_hero")

    service = WrappedService()
    png_bytes = service.generate_wrapped_card(stats)

    # Valid PNG bytes signature
    assert isinstance(png_bytes, bytes)
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    # Pillow image validation
    img = Image.open(io.BytesIO(png_bytes))
    assert img.format == "PNG"
    assert img.size == (1080, 1350)


# --- 4. Redis Caching Tests ---


@pytest.mark.asyncio
async def test_save_and_get_cached_wrapped():
    """Test saving and loading WrappedStats to/from Redis."""
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.get = AsyncMock()

    now = datetime.now(UTC)
    scan = ScanResult(session_id="cache-wrapped", scanned_at=now, total_unread=300)
    stats = WrappedService.calculate_wrapped_stats(scan)

    # Save
    await WrappedService.save_wrapped(mock_redis, stats, ttl=86400)
    mock_redis.setex.assert_awaited_once()
    assert mock_redis.setex.await_args[0][0] == "wrapped:cache-wrapped"
    assert mock_redis.setex.await_args[0][1] == 86400

    # Retrieve
    mock_redis.get.return_value = stats.model_dump_json().encode("utf-8")
    loaded = await WrappedService.get_cached_wrapped(mock_redis, "cache-wrapped")

    assert loaded is not None
    assert loaded.session_id == "cache-wrapped"
    assert loaded.archetype == ZenArchetype.DIGITAL_MONK
