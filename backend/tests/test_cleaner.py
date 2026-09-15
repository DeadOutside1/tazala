"""
Unit tests for Cleaner module:
- FolderRule title length validation (<= 12 chars)
- FloodSafeExecutor backoff and retry logic
- Batch mark_all_as_read filtering
- peer_map resolving for entity cache fix
- create_smart_folders preserving existing folders
- execute_zen_clean pipeline orchestration (with and without auto_logout)
- Expanded folder presets (7 categories, all langs)
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest

from app.cleaner.schemas import CleanConfig, FolderRule
from app.cleaner.service import CleanerService, get_smart_folder_presets
from app.scanner.schemas import ChatStatus, ChatType, DialogInfo, ScanResult
from app.telegram.session_store import SessionStore
from app.telegram.throttle import FloodSafeExecutor

# --- 1. FolderRule Validation Tests ---


def test_folder_rule_title_length_valid():
    """Test folder titles <= 12 characters are accepted."""
    rule1 = FolderRule(title="💼 Работа")
    assert rule1.title == "💼 Работа"
    assert len(rule1.title) <= 12

    rule2 = FolderRule(title="123456789012")
    assert len(rule2.title) == 12


def test_folder_rule_title_length_invalid():
    """Test folder titles > 12 characters raise ValidationError."""
    with pytest.raises(ValidationError):
        FolderRule(title="Слишком длинное название")


# --- 2. FloodSafeExecutor Tests ---


@pytest.mark.asyncio
async def test_flood_safe_executor_retry_success():
    """Test retry on FloodWaitError with backoff sleep, returning value on success."""
    flood_err = FloodWaitError(request=None)
    flood_err.seconds = 1

    calls = 0

    async def flaky_task():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise flood_err
        return "success_val"

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await FloodSafeExecutor.execute(flaky_task, max_retries=3, default_delay=0.1)

    assert result == "success_val"
    assert calls == 2
    # mock_sleep called for err.seconds + 1 (2s) and then default_delay (0.1s)
    mock_sleep.assert_any_await(2)
    mock_sleep.assert_any_await(0.1)


@pytest.mark.asyncio
async def test_flood_safe_executor_max_retries_exceeded():
    """Test exception is re-raised when max_retries is exceeded."""
    flood_err = FloodWaitError(request=None)
    flood_err.seconds = 0

    async def always_flood():
        raise flood_err

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(FloodWaitError):
            await FloodSafeExecutor.execute(always_flood, max_retries=2, default_delay=0.0)


# --- 3. mark_all_as_read Tests ---


@pytest.mark.asyncio
async def test_mark_all_as_read_only_unreads():
    """Test mark_all_as_read acknowledges only chats with unread_count > 0."""
    service = CleanerService()
    now = datetime.now(UTC)

    dialogs = [
        DialogInfo(
            id=101, title="Chat 1", type=ChatType.USER, unread_count=25,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
        DialogInfo(
            id=102, title="Chat 2", type=ChatType.CHANNEL, unread_count=0,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
        DialogInfo(
            id=103, title="Chat 3", type=ChatType.GROUP, unread_count=5,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
    ]

    mock_client = AsyncMock()
    mock_client.send_read_acknowledge = AsyncMock()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        total_marked = await service.mark_all_as_read(mock_client, dialogs, delay=0.01)

    assert total_marked == 30
    assert mock_client.send_read_acknowledge.await_count == 2
    mock_client.send_read_acknowledge.assert_any_await(101)
    mock_client.send_read_acknowledge.assert_any_await(103)


@pytest.mark.asyncio
async def test_mark_all_as_read_with_peer_map():
    """Test mark_all_as_read uses InputPeer from peer_map instead of bare int ID."""
    service = CleanerService()
    now = datetime.now(UTC)

    mock_peer_101 = MagicMock(name="InputPeer_101")
    mock_peer_103 = MagicMock(name="InputPeer_103")
    peer_map = {101: mock_peer_101, 103: mock_peer_103}

    dialogs = [
        DialogInfo(
            id=101, title="Chat 1", type=ChatType.USER, unread_count=10,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
        DialogInfo(
            id=103, title="Chat 3", type=ChatType.GROUP, unread_count=5,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
    ]

    mock_client = AsyncMock()
    mock_client.send_read_acknowledge = AsyncMock()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        total_marked = await service.mark_all_as_read(
            mock_client, dialogs, delay=0.01, peer_map=peer_map,
        )

    assert total_marked == 15
    # Should use InputPeer objects, not bare int IDs
    mock_client.send_read_acknowledge.assert_any_await(mock_peer_101)
    mock_client.send_read_acknowledge.assert_any_await(mock_peer_103)


# --- 4. create_smart_folders Tests ---


@pytest.mark.asyncio
async def test_create_smart_folders_preserves_existing():
    """Test smart folders creation preserves existing user folders and uses free IDs."""
    service = CleanerService()
    now = datetime.now(UTC)

    existing_filter = MagicMock()
    existing_filter.id = 2
    existing_filter.title = "Личное моё"

    mock_client = AsyncMock()

    async def fake_invoke(req):
        if isinstance(req, GetDialogFiltersRequest):
            resp = MagicMock()
            resp.filters = [existing_filter]
            return resp
        if isinstance(req, UpdateDialogFilterRequest):
            return True
        return None

    mock_client.side_effect = fake_invoke
    mock_client.get_input_entity = AsyncMock(return_value=MagicMock())

    dialogs = [
        # Work keyword channel
        DialogInfo(
            id=201, title="Dev & Code Chat", type=ChatType.CHANNEL, unread_count=0,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
        # News keyword channel
        DialogInfo(
            id=202, title="Global News Daily", type=ChatType.CHANNEL, unread_count=0,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
        # Personal user chat
        DialogInfo(
            id=203, title="Best Friend", type=ChatType.USER, unread_count=0,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
        # Dead channel
        DialogInfo(
            id=204, title="Old Desert", type=ChatType.CHANNEL, unread_count=0,
            last_message_date=now, status=ChatStatus.DEAD,
        ),
    ]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        created = await service.create_smart_folders(mock_client, dialogs)

    # Work, News, Personal and Dead folders should be created (no Finance/Study/Fun matches)
    assert "💼 Работа" in created
    assert "📰 Новости" in created
    assert "💬 Личные" in created
    assert "🗑 Мёртвые" in created


@pytest.mark.asyncio
async def test_create_smart_folders_with_peer_map():
    """Test create_smart_folders uses peer_map and skips get_input_entity calls."""
    service = CleanerService()
    now = datetime.now(UTC)

    mock_peer_201 = MagicMock(name="InputPeer_201")
    peer_map = {201: mock_peer_201}

    mock_client = AsyncMock()

    async def fake_invoke(req):
        if isinstance(req, GetDialogFiltersRequest):
            resp = MagicMock()
            resp.filters = []
            return resp
        if isinstance(req, UpdateDialogFilterRequest):
            return True
        return None

    mock_client.side_effect = fake_invoke
    # get_input_entity should NOT be called when peer_map has the entry
    mock_client.get_input_entity = AsyncMock(side_effect=ValueError("Should not be called"))

    dialogs = [
        DialogInfo(
            id=201, title="Dev & Code Chat", type=ChatType.CHANNEL, unread_count=0,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
    ]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        created = await service.create_smart_folders(
            mock_client, dialogs, peer_map=peer_map,
        )

    assert "💼 Работа" in created
    # Verify get_input_entity was NOT called (peer_map was used instead)
    mock_client.get_input_entity.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_smart_folders_with_selected_emojis():
    """Test create_smart_folders filters by selected_emojis."""
    service = CleanerService()
    now = datetime.now(UTC)

    mock_client = AsyncMock()

    async def fake_invoke(req):
        if isinstance(req, GetDialogFiltersRequest):
            resp = MagicMock()
            resp.filters = []
            return resp
        if isinstance(req, UpdateDialogFilterRequest):
            return True
        return None

    mock_client.side_effect = fake_invoke
    mock_client.get_input_entity = AsyncMock(return_value=MagicMock())

    dialogs = [
        DialogInfo(
            id=201, title="Dev Code", type=ChatType.CHANNEL, unread_count=0,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
        DialogInfo(
            id=203, title="Best Friend", type=ChatType.USER, unread_count=0,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
        DialogInfo(
            id=204, title="Dead Group", type=ChatType.CHANNEL, unread_count=0,
            last_message_date=now, status=ChatStatus.DEAD,
        ),
    ]

    # Only select Work and Dead — should NOT create Personal
    with patch("asyncio.sleep", new_callable=AsyncMock):
        created = await service.create_smart_folders(
            mock_client, dialogs, selected_emojis={"💼", "🗑"},
        )

    assert "💼 Работа" in created
    assert "🗑 Мёртвые" in created
    assert "💬 Личные" not in created


# --- 5. execute_zen_clean Pipeline Tests ---


@pytest.mark.asyncio
async def test_execute_zen_clean_no_logout():
    """Test full cleanup pipeline without auto-logout retains session."""
    service = CleanerService()
    mock_client = AsyncMock()
    mock_client.send_read_acknowledge = AsyncMock()
    # Mock get_dialogs for build_peer_map
    mock_dialog = MagicMock()
    mock_dialog.id = 301
    mock_dialog.input_entity = MagicMock()
    mock_client.get_dialogs = AsyncMock(return_value=[mock_dialog])

    mock_session_store = AsyncMock(spec=SessionStore)

    now = datetime.now(UTC)
    dialogs = [
        DialogInfo(
            id=301, title="Active Chat", type=ChatType.USER, unread_count=10,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
    ]
    scan_result = ScanResult(
        session_id="zen-sess-1",
        scanned_at=now,
        total_dialogs=1,
        total_unread=10,
        dialogs=dialogs,
    )

    config = CleanConfig(mark_read=True, create_folders=False, auto_logout=False)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await service.execute_zen_clean(
            client=mock_client,
            scan_result=scan_result,
            config=config,
            session_store=mock_session_store,
        )

    assert result.session_id == "zen-sess-1"
    assert result.messages_marked == 10
    assert result.session_destroyed is False
    mock_session_store.destroy.assert_not_awaited()
    # Verify get_dialogs was called for entity cache
    mock_client.get_dialogs.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_zen_clean_with_auto_logout():
    """Test full cleanup pipeline with auto_logout=True destroys session."""
    service = CleanerService()
    mock_client = AsyncMock()
    mock_client.get_dialogs = AsyncMock(return_value=[])
    mock_session_store = AsyncMock(spec=SessionStore)

    now = datetime.now(UTC)
    scan_result = ScanResult(
        session_id="zen-sess-logout",
        scanned_at=now,
        total_dialogs=0,
        dialogs=[],
    )

    config = CleanConfig(mark_read=False, create_folders=False, auto_logout=True)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await service.execute_zen_clean(
            client=mock_client,
            scan_result=scan_result,
            config=config,
            session_store=mock_session_store,
        )

    assert result.session_destroyed is True
    mock_session_store.destroy.assert_awaited_once_with("zen-sess-logout", mock_client)


@pytest.mark.asyncio
async def test_execute_zen_clean_populates_peer_map():
    """Test that execute_zen_clean calls get_dialogs to populate entity cache."""
    service = CleanerService()
    mock_client = AsyncMock()
    mock_client.send_read_acknowledge = AsyncMock()

    mock_dialog_1 = MagicMock()
    mock_dialog_1.id = 401
    mock_dialog_1.input_entity = MagicMock(name="Peer_401")

    mock_dialog_2 = MagicMock()
    mock_dialog_2.id = 402
    mock_dialog_2.input_entity = MagicMock(name="Peer_402")

    mock_client.get_dialogs = AsyncMock(return_value=[mock_dialog_1, mock_dialog_2])
    mock_session_store = AsyncMock(spec=SessionStore)

    now = datetime.now(UTC)
    dialogs = [
        DialogInfo(
            id=401, title="Unread 1", type=ChatType.USER, unread_count=50,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
        DialogInfo(
            id=402, title="Unread 2", type=ChatType.CHANNEL, unread_count=100,
            last_message_date=now, status=ChatStatus.ACTIVE,
        ),
    ]
    scan_result = ScanResult(
        session_id="peer-map-test",
        scanned_at=now,
        total_dialogs=2,
        total_unread=150,
        dialogs=dialogs,
    )

    config = CleanConfig(mark_read=True, create_folders=False, auto_logout=False)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await service.execute_zen_clean(
            client=mock_client,
            scan_result=scan_result,
            config=config,
            session_store=mock_session_store,
        )

    assert result.messages_marked == 150
    mock_client.get_dialogs.assert_awaited_once_with(limit=None)
    # Verify InputPeer objects were passed (not bare ints)
    calls = mock_client.send_read_acknowledge.call_args_list
    args_used = [call.args[0] if call.args else call.kwargs.get("entity") for call in calls]
    assert mock_dialog_1.input_entity in args_used
    assert mock_dialog_2.input_entity in args_used


# --- 6. Expanded Folder Presets Tests ---


def test_expanded_folder_presets_ru():
    """Test Russian presets have 7 categories with valid titles."""
    presets = get_smart_folder_presets("ru")
    assert len(presets) == 7
    emojis = [p.emoji for p in presets]
    assert "💼" in emojis
    assert "📰" in emojis
    assert "💰" in emojis
    assert "📚" in emojis
    assert "🎮" in emojis
    assert "💬" in emojis
    assert "🗑" in emojis
    for p in presets:
        assert len(p.title) <= 12, f"Title '{p.title}' exceeds 12 chars ({len(p.title)})"


def test_expanded_folder_presets_kk():
    """Test Kazakh presets have 7 categories with valid titles."""
    presets = get_smart_folder_presets("kk")
    assert len(presets) == 7
    for p in presets:
        assert len(p.title) <= 12, f"Title '{p.title}' exceeds 12 chars ({len(p.title)})"


def test_expanded_folder_presets_en():
    """Test English presets have 7 categories with valid titles."""
    presets = get_smart_folder_presets("en")
    assert len(presets) == 7
    for p in presets:
        assert len(p.title) <= 12, f"Title '{p.title}' exceeds 12 chars ({len(p.title)})"
