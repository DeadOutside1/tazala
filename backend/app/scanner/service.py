"""
Scanner Service for Telegram account diagnostics and dialog classification.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from redis.asyncio import Redis
from telethon import TelegramClient

from app.scanner.schemas import ChatStatus, ChatType, DialogInfo, ScanResult, TopUnreadChat

logger = logging.getLogger(__name__)


class ScannerService:
    """Performs deep scan of Telegram account dialogs and classifies activity."""

    @staticmethod
    def classify_dialog(
        dialog_type: ChatType,
        last_date: datetime | None,
        now: datetime,
    ) -> ChatStatus:
        """
        Classify dialog activity state based on chat type and days since last message.
        
        Rules:
        - No date: ZOMBIE for channel/group, DEAD for user/bot.
        - <= 30 days: ACTIVE
        - 31-180 days: MODERATE
        - Channels/groups > 365 days: ZOMBIE, 181-365 days: DEAD
        - Others > 180 days: DEAD
        """
        if last_date is None:
            if dialog_type in (ChatType.CHANNEL, ChatType.GROUP):
                return ChatStatus.ZOMBIE
            return ChatStatus.DEAD

        # Ensure timezone consistency
        date_utc = (
            last_date.astimezone(UTC)
            if last_date.tzinfo
            else last_date.replace(tzinfo=UTC)
        )
        now_utc = (
            now.astimezone(UTC)
            if now.tzinfo
            else now.replace(tzinfo=UTC)
        )

        diff_days = (now_utc - date_utc).days

        if diff_days <= 30:
            return ChatStatus.ACTIVE
        if diff_days <= 180:
            return ChatStatus.MODERATE

        if dialog_type in (ChatType.CHANNEL, ChatType.GROUP):
            if diff_days > 365:
                return ChatStatus.ZOMBIE
            return ChatStatus.DEAD

        return ChatStatus.DEAD

    @staticmethod
    def _detect_chat_type(dialog: object) -> ChatType:
        """Detect ChatType from a Telethon dialog object."""
        if getattr(dialog, "is_user", False):
            entity = getattr(dialog, "entity", None)
            if getattr(entity, "bot", False):
                return ChatType.BOT
            return ChatType.USER
        if getattr(dialog, "is_group", False):
            return ChatType.GROUP
        if getattr(dialog, "is_channel", False):
            return ChatType.CHANNEL
        return ChatType.USER

    async def scan_account(
        self,
        client: TelegramClient,
        session_id: str,
        progress_callback: Callable[[int], Awaitable[None]] | None = None,
    ) -> ScanResult:
        """
        Scan all account dialogs using iter_dialogs(), collect metadata,
        classify activity status, and compile diagnostic metrics.
        """
        loop = asyncio.get_running_loop()
        start_time = loop.time()
        now = datetime.now(UTC)

        dialogs: list[DialogInfo] = []
        scanned_count = 0

        logger.info("Starting account scan for session %s...", session_id[:8])

        async for dialog in client.iter_dialogs():
            scanned_count += 1
            try:
                chat_type = self._detect_chat_type(dialog)

                # Ensure date is timezone-aware in UTC
                raw_date = getattr(dialog, "date", None)
                date_utc: datetime | None = None
                if raw_date:
                    date_utc = (
                        raw_date.astimezone(UTC)
                        if raw_date.tzinfo
                        else raw_date.replace(tzinfo=UTC)
                    )

                status = self.classify_dialog(chat_type, date_utc, now)
                unread = getattr(dialog, "unread_count", 0) or 0
                title = getattr(dialog, "name", None) or getattr(dialog, "title", None) or "Unknown"

                info = DialogInfo(
                    id=getattr(dialog, "id", 0),
                    title=title,
                    type=chat_type,
                    unread_count=unread,
                    last_message_date=date_utc,
                    is_archived=bool(getattr(dialog, "archived", False)),
                    is_pinned=bool(getattr(dialog, "pinned", False)),
                    folder_id=getattr(dialog, "folder_id", None),
                    status=status,
                )
                dialogs.append(info)

            except Exception as e:
                logger.warning(
                    "Error parsing dialog #%d in session %s: %s",
                    scanned_count,
                    session_id[:8],
                    e,
                )
                continue

            if progress_callback and scanned_count % 50 == 0:
                await progress_callback(scanned_count)

        total_dialogs = len(dialogs)
        total_unread = sum(d.unread_count for d in dialogs)
        dead_count = sum(1 for d in dialogs if d.status == ChatStatus.DEAD)
        zombie_count = sum(1 for d in dialogs if d.status == ChatStatus.ZOMBIE)
        active_count = sum(1 for d in dialogs if d.status == ChatStatus.ACTIVE)
        moderate_count = sum(1 for d in dialogs if d.status == ChatStatus.MODERATE)

        channels_count = sum(1 for d in dialogs if d.type == ChatType.CHANNEL)
        groups_count = sum(1 for d in dialogs if d.type == ChatType.GROUP)
        users_count = sum(1 for d in dialogs if d.type == ChatType.USER)
        bots_count = sum(1 for d in dialogs if d.type == ChatType.BOT)
        archived_count = sum(1 for d in dialogs if d.is_archived)

        dead_sum = dead_count + zombie_count
        dead_percentage = round((dead_sum / total_dialogs) * 100, 1) if total_dialogs > 0 else 0.0

        # Top 10 unread chats with unread_count > 0
        unread_dialogs = [d for d in dialogs if d.unread_count > 0]
        unread_dialogs.sort(key=lambda d: d.unread_count, reverse=True)
        top_unread_chats = [
            TopUnreadChat(
                id=d.id,
                title=d.title,
                unread_count=d.unread_count,
                type=d.type,
            )
            for d in unread_dialogs[:10]
        ]

        duration = round(loop.time() - start_time, 2)
        logger.info(
            "Scan complete for session %s: %d dialogs, %d unread in %.2fs",
            session_id[:8],
            total_dialogs,
            total_unread,
            duration,
        )

        return ScanResult(
            session_id=session_id,
            scanned_at=now,
            total_dialogs=total_dialogs,
            total_unread=total_unread,
            dead_count=dead_count,
            zombie_count=zombie_count,
            active_count=active_count,
            moderate_count=moderate_count,
            channels_count=channels_count,
            groups_count=groups_count,
            users_count=users_count,
            bots_count=bots_count,
            archived_count=archived_count,
            dead_percentage=dead_percentage,
            top_unread_chats=top_unread_chats,
            scan_duration_seconds=duration,
            dialogs=dialogs,
        )

    @staticmethod
    async def save_scan_result(redis: Redis, scan_result: ScanResult, ttl: int = 600) -> None:
        """Serialize ScanResult to JSON and cache in Redis with TTL."""
        key = f"scan:{scan_result.session_id}"
        await redis.setex(key, ttl, scan_result.model_dump_json())
        logger.info(
            "Scan result for session %s cached in Redis (TTL %ds)",
            scan_result.session_id[:8],
            ttl,
        )

    @staticmethod
    async def get_cached_scan(redis: Redis, session_id: str) -> ScanResult | None:
        """Retrieve and deserialize cached ScanResult from Redis."""
        key = f"scan:{session_id}"
        raw = await redis.get(key)
        if not raw:
            return None
        data = raw.decode() if isinstance(raw, bytes) else raw
        return ScanResult.model_validate_json(data)
