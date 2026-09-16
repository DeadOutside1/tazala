"""
Analytics, user feedback and admin metrics tracking service for Tazala.
Atomic Redis persistence + append-only disk logging (data/reviews.jsonl).
"""
import html
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from redis.asyncio import Redis

from app.analytics.schemas import AnalyticsSummary, ReviewItem

logger = logging.getLogger(__name__)


def _resolve_data_dir() -> Path:
    """Resolve data directory consistently across local and Docker environments."""
    if os.getenv("DATA_DIR"):
        return Path(os.getenv("DATA_DIR"))
    if Path("/app/data").is_dir():
        return Path("/app/data")
    repo_root = Path(__file__).resolve().parents[3]
    repo_data = repo_root / "data"
    if repo_data.is_dir():
        return repo_data
    backend_data = Path(__file__).resolve().parents[2] / "data"
    if backend_data.is_dir():
        return backend_data
    return Path("data")


def _get_reviews_file() -> Path:
    """Get absolute or relative path to persistent reviews.jsonl."""
    return _resolve_data_dir() / "reviews.jsonl"


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
        If user previously rated, updates their rating, adjusts ratings_sum,
        removes previous revision from recent_reviews list, and upserts on disk.
        """
        rating = max(1, min(5, rating))
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        clean_comment = comment.strip()[:1000]
        review = ReviewItem(
            user_id=user_id,
            username=username,
            rating=rating,
            comment=clean_comment,
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
                # Remove obsolete revision from recent_reviews list
                await redis.lrem("tazala:recent_reviews", 0, raw_prev)
            else:
                # First time rating: increment count and add to sum
                await redis.hincrby("tazala:metrics", "ratings_count", 1)
                await redis.hincrby("tazala:metrics", "ratings_sum", rating)

            # Store in per-user hash
            review_json = review.model_dump_json()
            await redis.hset("tazala:user_reviews", str(user_id), review_json)

            # Clean any existing entries for this user from recent_reviews list
            # to guarantee 1 user = 1 review uniqueness in the recent list
            existing_recents = await redis.lrange("tazala:recent_reviews", 0, 99) or []
            for item_raw in existing_recents:
                try:
                    data_str = item_raw.decode() if isinstance(item_raw, bytes) else item_raw
                    parsed = json.loads(data_str)
                    if int(parsed.get("user_id", 0)) == user_id:
                        await redis.lrem("tazala:recent_reviews", 0, item_raw)
                except Exception:
                    continue

            # Prepend to recent reviews list (keep latest 100 unique entries)
            await redis.lpush("tazala:recent_reviews", review_json)
            await redis.ltrim("tazala:recent_reviews", 0, 99)

            # Persist to disk in data/reviews.jsonl with 1 user = 1 review upsert
            try:
                target_file = _get_reviews_file()
                os.makedirs(target_file.parent, exist_ok=True)
                existing_map: dict[int, str] = {}
                if target_file.exists():
                    with open(target_file, encoding="utf-8") as f:
                        for line in f:
                            sline = line.strip()
                            if not sline:
                                continue
                            try:
                                d = json.loads(sline)
                                uid = int(d.get("user_id", 0))
                                if uid:
                                    existing_map[uid] = sline
                            except Exception:
                                continue

                existing_map[user_id] = review_json

                temp_file = target_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    for rline in existing_map.values():
                        f.write(rline + "\n")
                temp_file.replace(target_file)
            except Exception as fe:
                logger.warning("Failed persisting review to disk: %s", fe)

        except Exception as e:
            logger.error("Failed saving review in Redis: %s", e)

        return review

    @staticmethod
    async def get_summary(redis: Redis) -> AnalyticsSummary:
        """Compute aggregated analytics metrics with disk fallback on cold start."""
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

            # Disk fallback if Redis metrics are empty (e.g. cold start)
            if ratings_count == 0:
                try:
                    target_file = _get_reviews_file()
                    if target_file.exists():
                        disk_user_ratings: dict[int, int] = {}
                        with open(target_file, encoding="utf-8") as f:
                            for line in f:
                                sline = line.strip()
                                if not sline:
                                    continue
                                try:
                                    item = ReviewItem.model_validate_json(sline)
                                    disk_user_ratings[item.user_id] = item.rating
                                except Exception:
                                    continue
                        ratings_count = len(disk_user_ratings)
                        ratings_sum = sum(disk_user_ratings.values())
                except Exception:
                    pass

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
        """Fetch latest unique user reviews from Redis with fallback to disk."""
        seen_users: set[int] = set()
        reviews: list[ReviewItem] = []

        try:
            raw_items = await redis.lrange("tazala:recent_reviews", 0, 99) or []
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
        except Exception as e:
            logger.warning("Failed fetching recent reviews from Redis: %s", e)

        # Fallback to persistent disk file if Redis is empty
        if not reviews:
            try:
                target_file = _get_reviews_file()
                if target_file.exists():
                    with open(target_file, encoding="utf-8") as f:
                        lines = [line.strip() for line in f if line.strip()]
                    for line in reversed(lines):
                        try:
                            item = ReviewItem.model_validate_json(line)
                            if item.user_id not in seen_users:
                                seen_users.add(item.user_id)
                                reviews.append(item)
                            if len(reviews) >= limit:
                                break
                        except Exception:
                            continue
            except Exception as fe:
                logger.warning("Failed reading reviews from disk fallback: %s", fe)

        return reviews

    @staticmethod
    def format_dashboard(summary: AnalyticsSummary) -> str:
        """Format high-level analytics for admin dashboard using HTML."""
        stars_bar = "⭐" * int(round(summary.avg_rating)) if summary.avg_rating else "—"
        return (
            "👑 <b>Tazala Admin Dashboard</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>Аудитория и активность:</b>\n"
            f"• 👥 Уникальных пользователей: <b>{summary.total_users:,}</b>\n"
            f"• 🔍 Всего сканирований: <b>{summary.total_scans:,}</b>\n"
            f"• 🧹 Успешных очисток: <b>{summary.total_cleans:,}</b>\n\n"
            "📈 <b>Результаты работы бота:</b>\n"
            f"• ✉️ Сообщений прочитано: <b>{summary.messages_marked:,}</b>\n"
            f"• 📁 Смарт-папок создано: <b>{summary.folders_created:,}</b>\n"
            f"• ⏳ Сэкономлено времени: <b>{summary.time_saved_hours:,} ч.</b>\n\n"
            "⭐ <b>Оценка и отзывы:</b>\n"
            f"• Средний балл: <b>{summary.avg_rating} / 5.0</b> {stars_bar}\n"
            f"• Всего оценок: <b>{summary.ratings_count}</b>\n\n"
            "<i>Данные обновляются в реальном времени из Redis.</i>"
        )

    @staticmethod
    def format_reviews_list(reviews: list[ReviewItem]) -> str:
        """
        Format recent user reviews with safe truncation (<=150 chars per comment)
        and HTML character escaping to strictly prevent formatting crashes.
        """
        if not reviews:
            return "📝 <b>Отзывы пользователей:</b>\n\n<i>Пока нет оставленных отзывов.</i>"

        lines = ["📝 <b>Последние отзывы пользователей:</b>\n"]
        for idx, rev in enumerate(reviews, 1):
            stars = "⭐" * rev.rating
            safe_username = html.escape(rev.username) if rev.username else ""
            user_label = f"@{safe_username}" if safe_username else f"ID {rev.user_id}"

            raw_comment = rev.comment[:150]
            safe_comment = html.escape(raw_comment)
            if len(rev.comment) > 150:
                safe_comment += "..."

            comment_str = f"\n💬 <i>«{safe_comment}»</i>" if safe_comment else ""
            lines.append(
                f"<b>{idx}. {user_label}</b> — {stars} ({rev.rating}/5)\n"
                f"📅 <code>{html.escape(rev.created_at)}</code>{comment_str}\n"
            )

        return "\n".join(lines)

