"""
Analytics, user feedback and admin metrics tracking service for Tazala.
Atomic Redis persistence + append-only disk logging (data/reviews.jsonl).
"""
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from redis.asyncio import Redis

from app.analytics.schemas import AnalyticsSummary, ReviewItem

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
REVIEWS_FILE = DATA_DIR / "reviews.jsonl"


def _escape_md(text: str) -> str:
    """Escape Markdown special characters for safe Telegram Markdown rendering."""
    if not text:
        return ""
    for ch in ("\\", "_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text


class AnalyticsService:
    """Core service for usage analytics, ratings and reviews."""

    @staticmethod
    async def record_user(redis: Redis, user_id: int) -> None:
        """Track unique Telegram user ID in a Redis set."""
        if not user_id:
            return
        try:
            await redis.sadd("tazala:users", str(user_id))
        except Exception as e:
            logger.warning("Failed recording user %d in analytics: %s", user_id, e)

    @staticmethod
    async def record_scan(redis: Redis, user_id: int) -> None:
        """Increment total scans counter and ensure user is tracked."""
        try:
            if user_id:
                await redis.sadd("tazala:users", str(user_id))
            await redis.hincrby("tazala:metrics", "total_scans", 1)
        except Exception as e:
            logger.warning("Failed recording scan in analytics: %s", e)

    @staticmethod
    async def record_clean(
        redis: Redis,
        user_id: int,
        messages: int,
        folders: int,
        hours: float,
    ) -> None:
        """Atomically record successful cleanup metrics."""
        try:
            if user_id:
                await redis.sadd("tazala:users", str(user_id))
            await redis.hincrby("tazala:metrics", "total_cleans", 1)
            if messages > 0:
                await redis.hincrby("tazala:metrics", "messages_marked", int(messages))
            if folders > 0:
                await redis.hincrby("tazala:metrics", "folders_created", int(folders))
            if hours > 0:
                await redis.hincrbyfloat("tazala:metrics", "time_saved_hours", float(hours))
        except Exception as e:
            logger.warning("Failed recording cleanup in analytics: %s", e)

    @staticmethod
    async def save_review(
        redis: Redis,
        user_id: int,
        username: str | None,
        rating: int,
        comment: str = "",
    ) -> ReviewItem:
        """
        Record or update a user rating and review.
        Enforces 1 user = 1 review:
        If user previously rated, updates their rating and adjusts ratings_sum
        without incrementing ratings_count.
        """
        rating = max(1, min(5, rating))
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        review = ReviewItem(
            user_id=user_id,
            username=username,
            rating=rating,
            comment=comment.strip(),
            created_at=now_str,
        )

        try:
            # Check if user already reviewed before
            raw_prev = await redis.hget("tazala:user_reviews", str(user_id))
            if raw_prev:
                prev_data = (
                    json.loads(raw_prev.decode() if isinstance(raw_prev, bytes) else raw_prev)
                )
                prev_rating = int(prev_data.get("rating", 0))
                # Adjust sum by difference: rating - prev_rating (count remains the same)
                diff = rating - prev_rating
                if diff != 0:
                    await redis.hincrby("tazala:metrics", "ratings_sum", diff)
            else:
                # First time rating: increment count and add to sum
                await redis.hincrby("tazala:metrics", "ratings_count", 1)
                await redis.hincrby("tazala:metrics", "ratings_sum", rating)

            # Store in per-user hash
            review_json = review.model_dump_json()
            await redis.hset("tazala:user_reviews", str(user_id), review_json)

            # Prepend to recent reviews list (keep latest 100)
            await redis.lpush("tazala:recent_reviews", review_json)
            await redis.ltrim("tazala:recent_reviews", 0, 99)

            # Persist to disk in data/reviews.jsonl
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(REVIEWS_FILE, "a", encoding="utf-8") as f:
                    f.write(review_json + "\n")
            except Exception as fe:
                logger.warning("Failed appending review to %s: %s", REVIEWS_FILE, fe)

        except Exception as e:
            logger.error("Failed saving review in Redis: %s", e)

        return review

    @staticmethod
    async def get_summary(redis: Redis) -> AnalyticsSummary:
        """Compute aggregated analytics metrics."""
        try:
            total_users = await redis.scard("tazala:users")
            raw_metrics = await redis.hgetall("tazala:metrics") or {}

            # Decode bytes if needed
            metrics: dict[str, str] = {
                (k.decode() if isinstance(k, bytes) else str(k)): (
                    v.decode() if isinstance(v, bytes) else str(v)
                )
                for k, v in raw_metrics.items()
            }

            total_scans = int(metrics.get("total_scans", 0))
            total_cleans = int(metrics.get("total_cleans", 0))
            messages_marked = int(metrics.get("messages_marked", 0))
            folders_created = int(metrics.get("folders_created", 0))
            time_saved_hours = round(float(metrics.get("time_saved_hours", 0.0)), 1)
            ratings_count = int(metrics.get("ratings_count", 0))
            ratings_sum = int(metrics.get("ratings_sum", 0))

            avg_rating = (
                round(ratings_sum / ratings_count, 1) if ratings_count > 0 else 0.0
            )

            return AnalyticsSummary(
                total_users=total_users,
                total_scans=total_scans,
                total_cleans=total_cleans,
                messages_marked=messages_marked,
                folders_created=folders_created,
                time_saved_hours=time_saved_hours,
                ratings_count=ratings_count,
                avg_rating=avg_rating,
            )
        except Exception as e:
            logger.exception("Error computing analytics summary: %s", e)
            return AnalyticsSummary()

    @staticmethod
    async def get_recent_reviews(redis: Redis, limit: int = 10) -> list[ReviewItem]:
        """Fetch latest unique user reviews from Redis."""
        try:
            raw_items = await redis.lrange("tazala:recent_reviews", 0, 99) or []
            seen_users = set()
            reviews: list[ReviewItem] = []

            for raw in raw_items:
                data = raw.decode() if isinstance(raw, bytes) else raw
                try:
                    item = ReviewItem.model_validate_json(data)
                    if item.user_id not in seen_users:
                        seen_users.add(item.user_id)
                        reviews.append(item)
                    if len(reviews) >= limit:
                        break
                except Exception:
                    continue

            return reviews
        except Exception as e:
            logger.warning("Failed fetching recent reviews: %s", e)
            return []

    @staticmethod
    def format_dashboard(summary: AnalyticsSummary) -> str:
        """Format high-level analytics for admin dashboard."""
        stars_bar = "⭐" * int(round(summary.avg_rating)) if summary.avg_rating else "—"
        return (
            "👑 **Tazala Admin Dashboard**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 **Аудитория и активность:**\n"
            f"• 👥 Уникальных пользователей: **{summary.total_users:,}**\n"
            f"• 🔍 Всего сканирований: **{summary.total_scans:,}**\n"
            f"• 🧹 Успешных очисток: **{summary.total_cleans:,}**\n\n"
            "📈 **Результаты работы бота:**\n"
            f"• ✉️ Сообщений прочитано: **{summary.messages_marked:,}**\n"
            f"• 📁 Смарт-папок создано: **{summary.folders_created:,}**\n"
            f"• ⏳ Сэкономлено времени: **{summary.time_saved_hours:,} ч.**\n\n"
            "⭐ **Оценка и отзывы:**\n"
            f"• Средний балл: **{summary.avg_rating} / 5.0** {stars_bar}\n"
            f"• Всего оценок: **{summary.ratings_count}**\n\n"
            "_Данные обновляются в реальном времени из Redis._"
        )

    @staticmethod
    def format_reviews_list(reviews: list[ReviewItem]) -> str:
        """
        Format recent user reviews with safe truncation (<=150 chars per comment)
        and Markdown special character escaping to strictly prevent formatting crashes.
        """
        if not reviews:
            return "📝 **Отзывы пользователей:**\n\n_Пока нет оставленных отзывов._"

        lines = ["📝 **Последние отзывы пользователей:**\n"]
        for idx, rev in enumerate(reviews, 1):
            stars = "⭐" * rev.rating
            safe_username = _escape_md(rev.username) if rev.username else ""
            user_label = f"@{safe_username}" if safe_username else f"ID {rev.user_id}"

            raw_comment = rev.comment[:150]
            safe_comment = _escape_md(raw_comment)
            if len(rev.comment) > 150:
                safe_comment += "..."

            comment_str = f"\n💬 _{safe_comment}_" if safe_comment else ""
            lines.append(
                f"**{idx}. {user_label}** — {stars} ({rev.rating}/5)\n"
                f"📅 `{rev.created_at}`{comment_str}\n"
            )

        return "\n".join(lines)

