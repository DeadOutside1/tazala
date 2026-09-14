"""
Unit tests for the Scanner module:
- classify_dialog logic & boundary conditions
- scan_account aggregation, filtering, top unread ranking
- Error tolerance on corrupted/restricted dialogs
- Redis scan result serialization and caching
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scanner.schemas import ChatStatus, ChatType, ScanResult
from app.scanner.service import ScannerService

# --- Helper to create mock Telethon dialogs ---

def create_mock_dialog(
    dialog_id: int,
    name: str,
    dialog_type: ChatType,
    unread_count: int = 0,
    date: datetime | None = None,
    archived: bool = False,
    pinned: bool = False,
    folder_id: int | None = None,
) -> MagicMock:
    dialog = MagicMock()
    dialog.id = dialog_id
    dialog.name = name
    dialog.title = name
    dialog.unread_count = unread_count
    dialog.date = date
    dialog.archived = archived
    dialog.pinned = pinned
    dialog.folder_id = folder_id

    dialog.is_user = dialog_type in (ChatType.USER, ChatType.BOT)
    dialog.is_group = dialog_type == ChatType.GROUP
    dialog.is_channel = dialog_type == ChatType.CHANNEL

    entity = MagicMock()
    entity.bot = dialog_type == ChatType.BOT
    dialog.entity = entity

    return dialog


# --- 1. Classification Tests ---


def test_classify_dialog_boundaries():
    """Test boundary conditions and days elapsed for dialog classification."""
    service = ScannerService()
    now = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)

    # 0 days (recent today) -> ACTIVE
    assert service.classify_dialog(ChatType.USER, now, now) == ChatStatus.ACTIVE

    # 30 days exactly -> ACTIVE
    d30 = now - timedelta(days=30)
    assert service.classify_dialog(ChatType.CHANNEL, d30, now) == ChatStatus.ACTIVE

    # 31 days -> MODERATE
    d31 = now - timedelta(days=31)
    assert service.classify_dialog(ChatType.GROUP, d31, now) == ChatStatus.MODERATE

    # 180 days -> MODERATE
    d180 = now - timedelta(days=180)
    assert service.classify_dialog(ChatType.USER, d180, now) == ChatStatus.MODERATE

    # 181 days -> DEAD for users and channels (not yet 365 days for channels)
    d181 = now - timedelta(days=181)
    assert service.classify_dialog(ChatType.USER, d181, now) == ChatStatus.DEAD
    assert service.classify_dialog(ChatType.CHANNEL, d181, now) == ChatStatus.DEAD

    # 366 days -> ZOMBIE for channels/groups, DEAD for users
    d366 = now - timedelta(days=366)
    assert service.classify_dialog(ChatType.CHANNEL, d366, now) == ChatStatus.ZOMBIE
    assert service.classify_dialog(ChatType.GROUP, d366, now) == ChatStatus.ZOMBIE
    assert service.classify_dialog(ChatType.USER, d366, now) == ChatStatus.DEAD


def test_classify_dialog_none_date():
    """Test None date classifies channels/groups as ZOMBIE and others as DEAD."""
    service = ScannerService()
    now = datetime.now(UTC)

    assert service.classify_dialog(ChatType.CHANNEL, None, now) == ChatStatus.ZOMBIE
    assert service.classify_dialog(ChatType.GROUP, None, now) == ChatStatus.ZOMBIE
    assert service.classify_dialog(ChatType.USER, None, now) == ChatStatus.DEAD
    assert service.classify_dialog(ChatType.BOT, None, now) == ChatStatus.DEAD


# --- 2. Scan Account Tests ---


@pytest.mark.asyncio
async def test_scan_account_full_aggregation():
    """Test dialog iteration, counting, metrics calculation, and top unread ranking."""
    now = datetime.now(UTC)
    service = ScannerService()

    # Create 15 varied dialogs
    mock_dialogs = [
        # Channels
        create_mock_dialog(1, "News Channel", ChatType.CHANNEL, unread_count=150, date=now),
        create_mock_dialog(
            2, "Old Channel", ChatType.CHANNEL, unread_count=20, date=now - timedelta(days=200)
        ),
        create_mock_dialog(
            3, "Abandoned Channel", ChatType.CHANNEL, unread_count=0, date=now - timedelta(days=400)
        ),
        # Groups
        create_mock_dialog(
            4, "Dev Group", ChatType.GROUP, unread_count=80, date=now - timedelta(days=10)
        ),
        create_mock_dialog(
            5, "Inactive Group", ChatType.GROUP, unread_count=0, date=now - timedelta(days=500)
        ),
        # Users
        create_mock_dialog(
            6, "Alice", ChatType.USER, unread_count=5, date=now - timedelta(days=2)
        ),
        create_mock_dialog(
            7, "Bob", ChatType.USER, unread_count=0, date=now - timedelta(days=40)
        ),
        create_mock_dialog(
            8, "Charlie", ChatType.USER, unread_count=12, date=now - timedelta(days=210)
        ),
        # Bots
        create_mock_dialog(
            9, "AlertBot", ChatType.BOT, unread_count=45, date=now - timedelta(days=1)
        ),
        create_mock_dialog(
            10, "OldBot", ChatType.BOT, unread_count=0, date=None
        ),
    ]

    # Additional 5 dialogs with varying unreads to test top 10 truncation
    for i in range(11, 16):
        mock_dialogs.append(
            create_mock_dialog(i, f"User {i}", ChatType.USER, unread_count=i * 2, date=now)
        )

    # Async generator to simulate client.iter_dialogs()
    async def fake_iter_dialogs():
        for d in mock_dialogs:
            yield d

    mock_client = AsyncMock()
    mock_client.iter_dialogs = fake_iter_dialogs

    result = await service.scan_account(mock_client, session_id="test-session")

    assert result.session_id == "test-session"
    assert result.total_dialogs == 15
    assert result.channels_count == 3
    assert result.groups_count == 2
    assert result.users_count == 8
    assert result.bots_count == 2

    # Verify counts
    # Dead channels: 1 (#2), Dead users: 2 (#8, #10) -> dead_count = 3
    # Zombie channels: 1 (#3), Zombie groups: 1 (#5) -> zombie_count = 2
    assert result.dead_count == 3
    assert result.zombie_count == 2
    assert result.dead_percentage == round((5 / 15) * 100, 1)

    # Top unread verification: maximum 10 items, sorted by unread_count descending
    assert len(result.top_unread_chats) <= 10
    assert result.top_unread_chats[0].title == "News Channel"
    assert result.top_unread_chats[0].unread_count == 150

    # Ensure all in top_unread have unread_count > 0 and strictly descending
    unreads = [chat.unread_count for chat in result.top_unread_chats]
    assert unreads == sorted(unreads, reverse=True)
    assert all(count > 0 for count in unreads)


@pytest.mark.asyncio
async def test_scan_account_progress_callback():
    """Test that progress callback is triggered every 50 dialogs."""
    service = ScannerService()
    now = datetime.now(UTC)

    # Generate 55 dialogs
    mock_dialogs = [
        create_mock_dialog(i, f"Chat {i}", ChatType.USER, date=now)
        for i in range(55)
    ]

    async def fake_iter():
        for d in mock_dialogs:
            yield d

    mock_client = AsyncMock()
    mock_client.iter_dialogs = fake_iter

    progress_calls = []

    async def progress_cb(count: int) -> None:
        progress_calls.append(count)

    result = await service.scan_account(
        mock_client, session_id="prog-session", progress_callback=progress_cb
    )

    assert result.total_dialogs == 55
    # Should be called once at count == 50
    assert progress_calls == [50]


@pytest.mark.asyncio
async def test_scan_account_error_tolerance():
    """Test that an unparseable/faulty dialog does not break the scan process."""
    service = ScannerService()
    now = datetime.now(UTC)

    good_dialog_1 = create_mock_dialog(1, "Valid Chat 1", ChatType.USER, date=now)

    faulty_dialog = MagicMock()
    # Raise error when accessing is_user
    type(faulty_dialog).is_user = property(
        lambda self: (_ for _ in ()).throw(RuntimeError("Deactivated channel"))
    )

    good_dialog_2 = create_mock_dialog(2, "Valid Chat 2", ChatType.CHANNEL, date=now)

    async def fake_iter():
        yield good_dialog_1
        yield faulty_dialog
        yield good_dialog_2

    mock_client = AsyncMock()
    mock_client.iter_dialogs = fake_iter

    result = await service.scan_account(mock_client, session_id="err-session")

    # Faulty dialog was skipped safely; 2 valid dialogs processed
    assert result.total_dialogs == 2
    assert len(result.dialogs) == 2


# --- 3. Redis Caching Tests ---


@pytest.mark.asyncio
async def test_save_and_get_cached_scan():
    """Test serialization of ScanResult into Redis JSON and retrieval."""
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.get = AsyncMock()

    service = ScannerService()
    now = datetime.now(UTC)

    scan_result = ScanResult(
        session_id="cache-sess-1",
        scanned_at=now,
        total_dialogs=25,
        total_unread=120,
        dead_count=5,
        zombie_count=3,
        active_count=15,
        moderate_count=2,
        dead_percentage=32.0,
        scan_duration_seconds=1.45,
    )

    # Test saving
    await service.save_scan_result(mock_redis, scan_result, ttl=600)
    mock_redis.setex.assert_awaited_once()
    call_args = mock_redis.setex.await_args[0]
    assert call_args[0] == "scan:cache-sess-1"
    assert call_args[1] == 600
    assert "cache-sess-1" in call_args[2]

    # Test retrieval
    mock_redis.get.return_value = scan_result.model_dump_json().encode("utf-8")
    loaded = await service.get_cached_scan(mock_redis, "cache-sess-1")

    assert loaded is not None
    assert loaded.session_id == "cache-sess-1"
    assert loaded.total_dialogs == 25
    assert loaded.dead_percentage == 32.0

    # Test non-existent key
    mock_redis.get.return_value = None
    not_found = await service.get_cached_scan(mock_redis, "non-existent")
    assert not_found is None
