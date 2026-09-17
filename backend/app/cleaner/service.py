"""
Cleaner service: batch mark read with throttling and smart folders creation.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable

from telethon import TelegramClient
from telethon.tl import types
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest

from app.cleaner.schemas import (
    CleanConfig,
    CleanProgress,
    CleanResult,
    CleanStep,
    FolderRule,
    UserFolderInfo,
)
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
                title="💰 Қаржы",
                emoji="💰",
                categories=[ChatType.CHANNEL, ChatType.GROUP],
                keywords=[
                    "crypto", "btc", "eth", "крипта", "трейдинг",
                    "инвестиции", "money", "bank", "акции", "finance",
                ],
            ),
            FolderRule(
                title="📚 Оқу",
                emoji="📚",
                categories=[ChatType.CHANNEL, ChatType.GROUP],
                keywords=[
                    "курсы", "книги", "study", "education", "english",
                    "лекции", "сабақ", "оқу", "course",
                ],
            ),
            FolderRule(
                title="🎮 Ойын-сауық",
                emoji="🎮",
                categories=[ChatType.CHANNEL, ChatType.GROUP],
                keywords=[
                    "мемы", "юмор", "кино", "музыка", "games",
                    "развлечения", "мем", "fun", "movie",
                ],
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
                title="💰 Finance",
                emoji="💰",
                categories=[ChatType.CHANNEL, ChatType.GROUP],
                keywords=[
                    "crypto", "btc", "eth", "trading", "invest",
                    "money", "bank", "stocks", "finance",
                ],
            ),
            FolderRule(
                title="📚 Study",
                emoji="📚",
                categories=[ChatType.CHANNEL, ChatType.GROUP],
                keywords=[
                    "course", "book", "study", "education", "english",
                    "lecture", "learn", "tutorial",
                ],
            ),
            FolderRule(
                title="🎮 Fun",
                emoji="🎮",
                categories=[ChatType.CHANNEL, ChatType.GROUP],
                keywords=[
                    "memes", "humor", "movie", "music", "games",
                    "fun", "entertainment",
                ],
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
            keywords=["news", "media", "digest", "инфо", "новости", "сми"],
        ),
        FolderRule(
            title="💰 Финансы",
            emoji="💰",
            categories=[ChatType.CHANNEL, ChatType.GROUP],
            keywords=[
                "крипта", "crypto", "btc", "eth", "трейдинг",
                "инвестиции", "money", "bank", "акции", "finance",
            ],
        ),
        FolderRule(
            title="📚 Обучение",
            emoji="📚",
            categories=[ChatType.CHANNEL, ChatType.GROUP],
            keywords=[
                "курсы", "книги", "study", "education", "english",
                "лекции", "course", "learn",
            ],
        ),
        FolderRule(
            title="🎮 Мемы/Лайф",
            emoji="🎮",
            categories=[ChatType.CHANNEL, ChatType.GROUP],
            keywords=[
                "мемы", "юмор", "кино", "музыка", "games",
                "развлечения", "мем", "fun",
            ],
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

    @staticmethod
    async def build_peer_map(client: TelegramClient) -> dict[int, object]:
        """
        Force-populate Telethon's internal entity cache by calling get_dialogs().
        Returns a mapping of dialog_id -> InputPeer with valid access_hash.
        This is CRITICAL for ephemeral StringSession clients where the cache is empty.
        """
        peer_map: dict[int, object] = {}
        try:
            raw_dialogs = await client.get_dialogs(limit=None)
            for d in raw_dialogs:
                try:
                    if hasattr(d, "input_entity") and d.input_entity:
                        peer_map[d.id] = d.input_entity
                except Exception:
                    pass
            logger.info("Entity cache populated: %d peers resolved", len(peer_map))
        except Exception as e:
            logger.warning("Failed to populate entity cache: %s", e)
        return peer_map

    async def mark_all_as_read(
        self,
        client: TelegramClient,
        dialogs: list[DialogInfo],
        progress_callback: Callable[[CleanProgress], Awaitable[None]] | None = None,
        delay: float = 0.5,
        session_id: str = "",
        peer_map: dict[int, object] | None = None,
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
                # Use peer_map InputPeer (has access_hash) instead of bare int ID
                target = peer_map.get(dialog.id, dialog.id) if peer_map else dialog.id
                await FloodSafeExecutor.execute(
                    lambda t=target: client.send_read_acknowledge(t),
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

        logger.info(
            "mark_all_as_read complete: %d chats, %d messages in session %s",
            total,
            total_messages_marked,
            session_id[:8],
        )
        return total_messages_marked

    async def create_smart_folders(
        self,
        client: TelegramClient,
        dialogs: list[DialogInfo],
        progress_callback: Callable[[CleanProgress], Awaitable[None]] | None = None,
        session_id: str = "",
        lang: str = "ru",
        peer_map: dict[int, object] | None = None,
        selected_emojis: set[str] | None = None,
    ) -> list[str]:
        """
        Create categorized smart folders up to Telegram limits without overriding user folders.
        Free Telegram accounts allow up to 10 folders (IDs 2-10).

        Args:
            selected_emojis: If provided, only create folders whose emoji is in this set.
        """
        created_folders: list[str] = []

        try:
            filters_response = await client(GetDialogFiltersRequest())
            filters_list = (
                getattr(filters_response, "filters", [])
                or (filters_response if isinstance(filters_response, list) else [])
            )
            used_ids = {f.id for f in filters_list if hasattr(f, "id")}
            used_titles: set[str] = set()
            for f in filters_list:
                t = getattr(f, "title", None)
                if t is not None:
                    if hasattr(t, "text"):
                        used_titles.add(t.text)
                    elif isinstance(t, str):
                        used_titles.add(t)
        except Exception as e:
            logger.warning("Could not fetch existing dialog filters: %s", e)
            used_ids = set()
            used_titles = set()

        # Available folder IDs between 2 and 10 (0 and 1 are reserved)
        available_ids = [fid for fid in range(2, 11) if fid not in used_ids]
        presets = get_smart_folder_presets(lang)

        # Filter presets by user selection if provided
        if selected_emojis is not None:
            presets = [r for r in presets if r.emoji in selected_emojis]

        total_presets = len(presets)

        for rule in presets:
            if not available_ids and rule.title not in used_titles:
                logger.info("No free folder slots remaining (max 10).")
                break

            # Identify matching dialogs
            matching: list[DialogInfo] = []
            for d in dialogs:
                if rule.emoji == "🗑":
                    if d.status in (ChatStatus.DEAD, ChatStatus.ZOMBIE):
                        matching.append(d)
                elif rule.emoji == "💬":
                    if d.type == ChatType.USER:
                        matching.append(d)
                elif rule.emoji in ("💼", "📰", "💰", "📚", "🎮"):
                    if d.type in rule.categories:
                        title_lower = d.title.lower()
                        if any(kw in title_lower for kw in rule.keywords):
                            matching.append(d)

            # Telegram allows maximum 100 peers per folder for non-premium
            candidates = matching[:100]
            include_peers = []
            for d in candidates:
                try:
                    # Use peer_map for pre-resolved InputPeer (avoids ValueError)
                    peer = peer_map.get(d.id) if peer_map else None
                    if peer is None:
                        peer = await client.get_input_entity(d.id)
                    if peer:
                        include_peers.append(peer)
                except Exception as e:
                    logger.debug("Failed resolving InputPeer for %s (%d): %s", d.title, d.id, e)
                    continue

            # If folder already exists, update it with new peers if available
            if rule.title in used_titles:
                existing_filter = None
                for f in filters_list:
                    t = getattr(f, "title", None)
                    t_str = t.text if hasattr(t, "text") else str(t or "")
                    if t_str == rule.title:
                        existing_filter = f
                        break

                if existing_filter and include_peers:
                    existing_peers = getattr(existing_filter, "include_peers", []) or []
                    existing_filter.include_peers = list(existing_peers) + [
                        p for p in include_peers if p not in existing_peers
                    ][:max(0, 100 - len(existing_peers))]

                    try:
                        await FloodSafeExecutor.execute(
                            lambda fid=existing_filter.id, df=existing_filter: client(
                                UpdateDialogFilterRequest(id=fid, filter=df)
                            ),
                            default_delay=1.5,
                        )
                        logger.info("Updated existing folder '%s'", rule.title)
                    except Exception as e:
                        logger.warning("Failed updating folder '%s': %s", rule.title, e)

                created_folders.append(rule.title)
                continue

            free_id = available_ids.pop(0)
            title_val = (
                types.TextWithEntities(text=rule.title, entities=[])
                if hasattr(types, "TextWithEntities")
                else rule.title
            )
            dialog_filter = types.DialogFilter(
                id=free_id,
                title=title_val,
                pinned_peers=[],
                include_peers=include_peers,
                exclude_peers=[],
                emoticon=rule.emoji,
                contacts=(rule.emoji == "💬"),
                non_contacts=(rule.emoji == "💬"),
                groups=(ChatType.GROUP in rule.categories),
                broadcasts=(ChatType.CHANNEL in rule.categories),
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

        # CRITICAL: Force-populate entity cache for ephemeral StringSession clients.
        # Without this, send_read_acknowledge() and get_input_entity() fail with
        # "Could not find input entity" because the cache has no access_hash entries.
        peer_map = await self.build_peer_map(client)

        messages_marked = 0
        folders_created: list[str] = []

        if config.mark_read:
            messages_marked = await self.mark_all_as_read(
                client=client,
                dialogs=scan_result.dialogs,
                progress_callback=progress_callback,
                delay=config.delay_per_dialog,
                session_id=sid,
                peer_map=peer_map,
            )

        if config.create_folders:
            # Convert selected_folders list to set of emojis for filtering
            selected_emojis = (
                set(config.selected_folders) if config.selected_folders else None
            )
            folders_created = await self.create_smart_folders(
                client=client,
                dialogs=scan_result.dialogs,
                progress_callback=progress_callback,
                session_id=sid,
                lang=lang,
                peer_map=peer_map,
                selected_emojis=selected_emojis,
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

    async def get_user_folders(self, client: TelegramClient) -> list[UserFolderInfo]:
        """
        Fetch all user-created dialog folders from Telegram account.
        Filters out default non-custom tabs (id == 0 or DialogFilterDefault).
        """
        result = await client(GetDialogFiltersRequest())
        if hasattr(result, "filters"):
            raw_filters = result.filters
        elif isinstance(result, list):
            raw_filters = result
        else:
            raw_filters = []

        user_folders: list[UserFolderInfo] = []
        for f in raw_filters:
            fid = getattr(f, "id", None)
            if fid is None or fid == 0:
                continue

            title_attr = getattr(f, "title", None)
            if title_attr is None:
                continue
            title_str = title_attr.text if hasattr(title_attr, "text") else str(title_attr)

            emoticon = getattr(f, "emoticon", None)
            include_peers = getattr(f, "include_peers", []) or []
            pinned_peers = getattr(f, "pinned_peers", []) or []
            chats_count = len(include_peers) + len(pinned_peers)

            user_folders.append(
                UserFolderInfo(
                    id=int(fid),
                    title=title_str,
                    emoticon=emoticon,
                    chats_count=chats_count,
                )
            )

        return user_folders

    async def rename_folder(
        self,
        client: TelegramClient,
        folder_id: int,
        new_title: str,
    ) -> UserFolderInfo:
        """
        Rename an existing dialog folder strictly respecting the <=12 characters limit.
        """
        new_title = new_title.strip()
        if len(new_title) > 12:
            raise ValueError(
                f"Folder title '{new_title}' exceeds 12 characters limit ({len(new_title)} chars)"
            )

        result = await client(GetDialogFiltersRequest())
        if hasattr(result, "filters"):
            raw_filters = result.filters
        elif isinstance(result, list):
            raw_filters = result
        else:
            raw_filters = []

        target_filter = None
        for f in raw_filters:
            if getattr(f, "id", None) == folder_id:
                target_filter = f
                break

        if not target_filter:
            raise ValueError(f"Folder with id {folder_id} not found")

        title_val = (
            types.TextWithEntities(text=new_title, entities=[])
            if hasattr(types, "TextWithEntities")
            else new_title
        )
        target_filter.title = title_val

        await FloodSafeExecutor.execute(
            lambda: client(UpdateDialogFilterRequest(id=folder_id, filter=target_filter)),
            default_delay=1.0,
        )
        logger.info("Successfully renamed folder %d to '%s'", folder_id, new_title)
        include_peers = getattr(target_filter, "include_peers", []) or []
        pinned_peers = getattr(target_filter, "pinned_peers", []) or []
        return UserFolderInfo(
            id=folder_id,
            title=new_title,
            emoticon=getattr(target_filter, "emoticon", None),
            chats_count=len(include_peers) + len(pinned_peers),
        )

    async def delete_folder(self, client: TelegramClient, folder_id: int) -> bool:
        """
        Delete a dialog filter by passing filter=None to UpdateDialogFilterRequest.
        Does NOT delete actual chats or messages.
        """
        await FloodSafeExecutor.execute(
            lambda: client(UpdateDialogFilterRequest(id=folder_id, filter=None)),
            default_delay=1.0,
        )
        logger.info("Successfully deleted folder %d", folder_id)
        return True
