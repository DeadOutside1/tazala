"""
Cleaner service: batch mark read with throttling and smart folders creation.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable

from telethon import TelegramClient
from telethon.tl import types
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest

from app.cleaner.schemas import CleanConfig, CleanProgress, CleanResult, CleanStep, FolderRule
from app.scanner.schemas import ChatStatus, ChatType, DialogInfo, ScanResult
from app.telegram.session_store import SessionStore
from app.telegram.throttle import FloodSafeExecutor

logger = logging.getLogger(__name__)

def get_smart_folder_presets(lang: str = "ru") -> list[FolderRule]:
    """Return smart folder rules tailored to user language (strictly <= 12 chars)."""
    if lang == "kk":
        return [
            FolderRule(
                title="💼 Жұмыс",
                emoji="💼",
                categories=[ChatType.CHANNEL, ChatType.GROUP],
                keywords=["work", "job", "hr", "dev", "code", "it", "qa", "жұмыс", "қызмет"],
            ),
            FolderRule(
                title="📰 Жаңалық",
                emoji="📰",
                categories=[ChatType.CHANNEL],
                keywords=["news", "media", "digest", "жаңалық", "хабар", "ақпарат"],
            ),
            FolderRule(
                title="💬 Жеке",
                emoji="💬",
                categories=[ChatType.USER],
                keywords=[],
            ),
            FolderRule(
                title="🗑 Өлі чаттар",
                emoji="🗑",
                categories=[],
                keywords=[],
            ),
        ]
    if lang == "en":
        return [
            FolderRule(
                title="💼 Work",
                emoji="💼",
                categories=[ChatType.CHANNEL, ChatType.GROUP],
                keywords=["work", "job", "hr", "dev", "code", "it", "qa"],
            ),
            FolderRule(
                title="📰 News",
                emoji="📰",
                categories=[ChatType.CHANNEL],
                keywords=["news", "media", "digest", "daily", "times"],
            ),
            FolderRule(
                title="💬 Personal",
                emoji="💬",
                categories=[ChatType.USER],
                keywords=[],
            ),
            FolderRule(
                title="🗑 Inactive",
                emoji="🗑",
                categories=[],
                keywords=[],
            ),
        ]
    # Default: ru
    return [
        FolderRule(
            title="💼 Работа",
            emoji="💼",
            categories=[ChatType.CHANNEL, ChatType.GROUP],
            keywords=["work", "job", "hr", "dev", "code", "it", "qa", "работа"],
        ),
        FolderRule(
            title="📰 Новости",
            emoji="📰",
            categories=[ChatType.CHANNEL],
            keywords=["news", "media", "digest", "инфо", "новости"],
        ),
        FolderRule(
            title="💬 Личные",
            emoji="💬",
            categories=[ChatType.USER],
            keywords=[],
        ),
        FolderRule(
            title="🗑 Мёртвые",
            emoji="🗑",
            categories=[],
            keywords=[],
        ),
    ]


SMART_FOLDER_PRESETS = get_smart_folder_presets("ru")


class CleanerService:
    """Orchestrates account cleanup: batch read acknowledgment and folder organization."""

    get_smart_folder_presets = staticmethod(get_smart_folder_presets)

    async def mark_all_as_read(
        self,
        client: TelegramClient,
        dialogs: list[DialogInfo],
        progress_callback: Callable[[CleanProgress], Awaitable[None]] | None = None,
        delay: float = 0.5,
        session_id: str = "",
    ) -> int:
        """Mark unread dialogs as read safely using FloodSafeExecutor."""
        unread_dialogs = [d for d in dialogs if d.unread_count > 0]
        total = len(unread_dialogs)
        total_messages_marked = 0

        logger.info(
            "Starting mark-as-read for %d dialogs in session %s",
            total,
            session_id[:8],
        )

        for i, dialog in enumerate(unread_dialogs, 1):
            try:
                target_id = dialog.id
                await FloodSafeExecutor.execute(
                    lambda tid=target_id: client.send_read_acknowledge(tid),
                    default_delay=delay,
                )
                total_messages_marked += dialog.unread_count
            except Exception as e:
                logger.warning(
                    "Failed to mark read for dialog %s (%d): %s",
                    dialog.title,
                    dialog.id,
                    e,
                )

            if progress_callback:
                await progress_callback(
                    CleanProgress(
                        session_id=session_id,
                        step=CleanStep.MARK_READ,
                        current=i,
                        total=total,
                        message=f"Marked as read: {dialog.title[:15]}",
                    )
                )

        return total_messages_marked

    async def create_smart_folders(
        self,
        client: TelegramClient,
        dialogs: list[DialogInfo],
        progress_callback: Callable[[CleanProgress], Awaitable[None]] | None = None,
        session_id: str = "",
        lang: str = "ru",
    ) -> list[str]:
        """
        Create categorized smart folders up to Telegram limits without overriding user folders.
        Free Telegram accounts allow up to 10 folders (IDs 2-10).
        """
        created_folders: list[str] = []

        try:
            filters_response = await client(GetDialogFiltersRequest())
            filters_list = (
                getattr(filters_response, "filters", [])
                or (filters_response if isinstance(filters_response, list) else [])
            )
            used_ids = {f.id for f in filters_list if hasattr(f, "id")}
            used_titles = {
                getattr(f, "title", None) for f in filters_list if hasattr(f, "title")
            }
        except Exception as e:
            logger.warning("Could not fetch existing dialog filters: %s", e)
            used_ids = set()
            used_titles = set()

        # Available folder IDs between 2 and 10 (0 and 1 are reserved)
        available_ids = [fid for fid in range(2, 11) if fid not in used_ids]
        presets = get_smart_folder_presets(lang)
        total_presets = len(presets)

        for rule in presets:
            if not available_ids:
                logger.info("No free folder slots remaining (max 10).")
                break

            if rule.title in used_titles:
                logger.info("Folder '%s' already exists, skipping.", rule.title)
                continue

            # Identify matching dialogs
            matching: list[DialogInfo] = []
            for d in dialogs:
                if rule.emoji == "🗑":
                    if d.status in (ChatStatus.DEAD, ChatStatus.ZOMBIE):
                        matching.append(d)
                elif rule.emoji == "💬":
                    if d.type == ChatType.USER:
                        matching.append(d)
                elif rule.emoji in ("💼", "📰"):
                    if d.type in rule.categories:
                        title_lower = d.title.lower()
                        if any(kw in title_lower for kw in rule.keywords):
                            matching.append(d)

            if not matching:
                continue

            # Telegram allows maximum 100 peers per folder for non-premium
            candidates = matching[:100]
            include_peers = []
            for d in candidates:
                try:
                    peer = await client.get_input_entity(d.id)
                    if peer:
                        include_peers.append(peer)
                except Exception as e:
                    logger.debug("Failed resolving InputPeer for %s (%d): %s", d.title, d.id, e)
                    continue

            if not include_peers:
                continue

            free_id = available_ids.pop(0)
            dialog_filter = types.DialogFilter(
                id=free_id,
                title=rule.title,
                pinned_peers=[],
                include_peers=include_peers,
                exclude_peers=[],
            )

            try:
                await FloodSafeExecutor.execute(
                    lambda fid=free_id, df=dialog_filter: client(
                        UpdateDialogFilterRequest(id=fid, filter=df)
                    ),
                    default_delay=1.5,
                )
                created_folders.append(rule.title)
                used_titles.add(rule.title)
                used_ids.add(free_id)
                logger.info("Created folder '%s' with %d chats", rule.title, len(include_peers))
            except Exception as e:
                logger.error("Failed creating folder '%s': %s", rule.title, e)

            if progress_callback:
                await progress_callback(
                    CleanProgress(
                        session_id=session_id,
                        step=CleanStep.CREATE_FOLDERS,
                        current=len(created_folders),
                        total=total_presets,
                        message=f"Created folder: {rule.title}",
                    )
                )

        return created_folders

    async def execute_zen_clean(
        self,
        client: TelegramClient,
        scan_result: ScanResult,
        config: CleanConfig,
        session_store: SessionStore,
        progress_callback: Callable[[CleanProgress], Awaitable[None]] | None = None,
        lang: str = "ru",
    ) -> CleanResult:
        """Main orchestrator for the Zen Cleanup pipeline."""
        loop = asyncio.get_running_loop()
        start_time = loop.time()
        sid = scan_result.session_id

        messages_marked = 0
        folders_created: list[str] = []

        if config.mark_read:
            messages_marked = await self.mark_all_as_read(
                client=client,
                dialogs=scan_result.dialogs,
                progress_callback=progress_callback,
                delay=config.delay_per_dialog,
                session_id=sid,
            )

        if config.create_folders:
            folders_created = await self.create_smart_folders(
                client=client,
                dialogs=scan_result.dialogs,
                progress_callback=progress_callback,
                session_id=sid,
                lang=lang,
            )

        session_destroyed = False
        if config.auto_logout:
            if progress_callback:
                await progress_callback(
                    CleanProgress(
                        session_id=sid,
                        step=CleanStep.LOGOUT,
                        current=1,
                        total=1,
                        message="Destroying session key (Zero-Knowledge)",
                    )
                )
            await session_store.destroy(sid, client)
            session_destroyed = True

        if progress_callback:
            await progress_callback(
                CleanProgress(
                    session_id=sid,
                    step=CleanStep.COMPLETED,
                    current=1,
                    total=1,
                    message="Cleanup finished successfully",
                )
            )

        duration = round(loop.time() - start_time, 2)
        return CleanResult(
            session_id=sid,
            messages_marked=messages_marked,
            folders_created=folders_created,
            duration_seconds=duration,
            session_destroyed=session_destroyed,
        )
