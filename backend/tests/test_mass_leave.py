"""
Unit and integration tests for Nuclear Button (Mass Leave Dead/Zombie Channels):
- mass_leave_dead_channels logic (filtering DEAD & ZOMBIE channels/groups only)
- selective leave via selected_ids parameter
- ignoring personal chats (ChatType.USER)
- error tolerance / resilience on individual chat failures
- keyboard structures: diagnostic prompt, choice menu, interactive browser, confirmation
- localization in RU, KK, EN
- bot callback handlers (choice, all prompt, browse, toggle, page, bulk selection, leave)
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.bot.handlers import (
    cb_dead_all_prompt,
    cb_dead_browse,
    cb_dead_cancel,
    cb_dead_confirm_leave,
    cb_dead_confirm_selected,
    cb_dead_leave_prompt,
    cb_dead_page,
    cb_dead_page_bulk_selection,
    cb_dead_toggle,
)
from app.bot.i18n.manager import i18n
from app.bot.keyboards import (
    get_dead_channels_browse_kb,
    get_dead_choice_kb,
    get_dead_leave_confirm_kb,
    get_diagnostic_kb,
)
from app.bot.states import AppSG
from app.cleaner.schemas import CleanStep
from app.cleaner.service import CleanerService
from app.scanner.schemas import ChatStatus, ChatType, DialogInfo, ScanResult


@pytest.fixture
def sample_mixed_dialogs() -> list[DialogInfo]:
    """Sample list with channels, groups, and personal chats in various statuses."""
    now = datetime.now(UTC)
    return [
        DialogInfo(
            id=101,
            title="Dead Tech Channel",
            type=ChatType.CHANNEL,
            unread_count=50,
            status=ChatStatus.DEAD,
            last_message_date=now,
        ),
        DialogInfo(
            id=102,
            title="Zombie Discussion Group",
            type=ChatType.GROUP,
            unread_count=10,
            status=ChatStatus.ZOMBIE,
            last_message_date=now,
        ),
        DialogInfo(
            id=103,
            title="Active News Channel",
            type=ChatType.CHANNEL,
            unread_count=5,
            status=ChatStatus.ACTIVE,
            last_message_date=now,
        ),
        DialogInfo(
            id=104,
            title="Inactive Personal Friend",
            type=ChatType.USER,
            unread_count=0,
            status=ChatStatus.DEAD,
            last_message_date=now,
        ),
        DialogInfo(
            id=105,
            title="Moderate Work Group",
            type=ChatType.GROUP,
            unread_count=2,
            status=ChatStatus.MODERATE,
            last_message_date=now,
        ),
    ]


# --- 1. Service Layer Tests ---


@pytest.mark.asyncio
async def test_mass_leave_dead_channels_success(sample_mixed_dialogs):
    """Test that mass_leave unsubscribes ONLY from DEAD/ZOMBIE channels and groups."""
    mock_client = AsyncMock()
    mock_client.delete_dialog = AsyncMock()

    progress_calls = []

    async def on_progress(p):
        progress_calls.append(p)

    service = CleanerService()
    peer_map = {101: "peer_101", 102: "peer_102"}

    left_count = await service.mass_leave_dead_channels(
        client=mock_client,
        dialogs=sample_mixed_dialogs,
        peer_map=peer_map,
        progress_callback=on_progress,
        delay=0.0,
        session_id="test_sess",
    )

    assert left_count == 2
    assert mock_client.delete_dialog.await_count == 2

    called_peers = [call.args[0] for call in mock_client.delete_dialog.await_args_list]
    assert "peer_101" in called_peers
    assert "peer_102" in called_peers

    # Ensure progress callback reported LEAVE_CHANNELS step
    assert len(progress_calls) == 2
    assert all(p.step == CleanStep.LEAVE_CHANNELS for p in progress_calls)
    assert progress_calls[-1].current == 2
    assert progress_calls[-1].total == 2


@pytest.mark.asyncio
async def test_mass_leave_dead_channels_selected_ids_only(sample_mixed_dialogs):
    """Test selective mass_leave unsubscribes ONLY from chosen dead channels/groups."""
    mock_client = AsyncMock()
    mock_client.delete_dialog = AsyncMock()

    service = CleanerService()
    peer_map = {101: "peer_101", 102: "peer_102"}

    # Only select channel 101, excluding group 102
    left_count = await service.mass_leave_dead_channels(
        client=mock_client,
        dialogs=sample_mixed_dialogs,
        peer_map=peer_map,
        selected_ids={101},
        delay=0.0,
        session_id="test_sess",
    )

    assert left_count == 1
    assert mock_client.delete_dialog.await_count == 1
    assert mock_client.delete_dialog.await_args[0][0] == "peer_101"


@pytest.mark.asyncio
async def test_mass_leave_ignores_personal_user_chats():
    """Verify personal chats (ChatType.USER) are NEVER deleted, even if DEAD or ZOMBIE."""
    mock_client = AsyncMock()
    mock_client.delete_dialog = AsyncMock()

    now = datetime.now(UTC)
    user_dialogs = [
        DialogInfo(
            id=201,
            title="Old Friend",
            type=ChatType.USER,
            status=ChatStatus.DEAD,
            last_message_date=now,
        ),
        DialogInfo(
            id=202,
            title="Ex Colleague",
            type=ChatType.USER,
            status=ChatStatus.ZOMBIE,
            last_message_date=now,
        ),
    ]

    service = CleanerService()
    left_count = await service.mass_leave_dead_channels(
        client=mock_client,
        dialogs=user_dialogs,
        delay=0.0,
    )

    assert left_count == 0
    mock_client.delete_dialog.assert_not_awaited()


@pytest.mark.asyncio
async def test_mass_leave_error_handling_resilience():
    """Test that a failure on one channel does not stop mass leaving the rest."""
    mock_client = AsyncMock()

    async def mock_delete_dialog(peer):
        if peer == 301:
            raise RuntimeError("Telegram API error / Channel inaccessible")
        return True

    async def mock_client_call(req):
        if hasattr(req, "channel") and req.channel == 301:
            raise RuntimeError("Fallback also failed")
        return True

    mock_client.delete_dialog = AsyncMock(side_effect=mock_delete_dialog)
    mock_client.side_effect = mock_client_call

    now = datetime.now(UTC)
    dialogs = [
        DialogInfo(
            id=301,
            title="Broken Channel",
            type=ChatType.CHANNEL,
            status=ChatStatus.DEAD,
            last_message_date=now,
        ),
        DialogInfo(
            id=302,
            title="Normal Dead Channel",
            type=ChatType.CHANNEL,
            status=ChatStatus.DEAD,
            last_message_date=now,
        ),
    ]

    service = CleanerService()
    left_count = await service.mass_leave_dead_channels(
        client=mock_client,
        dialogs=dialogs,
        delay=0.0,
    )

    assert left_count == 1
    assert mock_client.delete_dialog.await_count == 2


# --- 2. Keyboards & Localization Tests ---


def test_diagnostic_keyboard_with_dead_channels():
    """Test get_diagnostic_kb renders Nuclear Button only when dead_count > 0."""
    kb_no_dead = get_diagnostic_kb(unread_count=100, dead_count=0, lang="ru")
    assert all(
        "dead:leave_prompt" != btn.callback_data
        for row in kb_no_dead.inline_keyboard
        for btn in row
    )

    kb_with_dead = get_diagnostic_kb(unread_count=100, dead_count=15, lang="ru")
    dead_buttons = [
        btn
        for row in kb_with_dead.inline_keyboard
        for btn in row
        if btn.callback_data == "dead:leave_prompt"
    ]
    assert len(dead_buttons) == 1
    assert "15" in dead_buttons[0].text
    assert "💣" in dead_buttons[0].text


def test_dead_choice_keyboard_structure():
    """Test choice keyboard options: 1-click fast, manual browser, cancel."""
    kb = get_dead_choice_kb(dead_count=10, lang="ru")
    assert len(kb.inline_keyboard) == 3
    assert kb.inline_keyboard[0][0].callback_data == "dead:all_prompt"
    assert "10" in kb.inline_keyboard[0][0].text
    assert kb.inline_keyboard[1][0].callback_data == "dead:browse:0"
    assert kb.inline_keyboard[2][0].callback_data == "dead:cancel"


def test_dead_channels_browse_keyboard_pagination_and_checkboxes():
    """Test interactive browser keyboard layout, pagination buttons and checkboxes."""
    now = datetime.now(UTC)
    dialogs = [
        DialogInfo(
            id=i,
            title=f"Channel {i}",
            type=ChatType.CHANNEL,
            status=ChatStatus.DEAD,
            last_message_date=now,
        )
        for i in range(1, 11)  # 10 dialogs, per_page=8 => 2 pages
    ]
    selected_ids = {1, 3, 9}

    # --- Page 0 (dialogs 1..8) ---
    kb_p0 = get_dead_channels_browse_kb(
        dialogs=dialogs,
        selected_ids=selected_ids,
        page=0,
        per_page=8,
        lang="ru",
    )
    # 8 dialog rows + nav row + bulk row + confirm row + back row = 12 rows
    assert len(kb_p0.inline_keyboard) == 12

    # Check dialog 1 is checked (✅), dialog 2 is unchecked (⬜)
    assert "✅" in kb_p0.inline_keyboard[0][0].text
    assert kb_p0.inline_keyboard[0][0].callback_data == "dead:toggle:1:0"
    assert "⬜" in kb_p0.inline_keyboard[1][0].text
    assert kb_p0.inline_keyboard[1][0].callback_data == "dead:toggle:2:0"
    assert "✅" in kb_p0.inline_keyboard[2][0].text
    assert kb_p0.inline_keyboard[2][0].callback_data == "dead:toggle:3:0"

    # Navigation row: counter and Next button
    nav_row = kb_p0.inline_keyboard[8]
    assert len(nav_row) == 2
    assert "1 / 2" in nav_row[0].text
    assert nav_row[0].callback_data == "dead:noop"
    assert nav_row[1].callback_data == "dead:page:1"

    # Bulk row: select page and deselect page
    bulk_row = kb_p0.inline_keyboard[9]
    assert bulk_row[0].callback_data == "dead:select_page:0"
    assert bulk_row[1].callback_data == "dead:deselect_page:0"

    # Confirm row with count 3
    confirm_row = kb_p0.inline_keyboard[10]
    assert confirm_row[0].callback_data == "dead:confirm_selected"
    assert "3" in confirm_row[0].text

    # Back row returns to dead:leave_prompt
    assert kb_p0.inline_keyboard[11][0].callback_data == "dead:leave_prompt"

    # --- Page 1 (dialogs 9..10) ---
    kb_p1 = get_dead_channels_browse_kb(
        dialogs=dialogs,
        selected_ids=selected_ids,
        page=1,
        per_page=8,
        lang="ru",
    )
    # 2 dialog rows + nav row + bulk row + confirm row + back row = 6 rows
    assert len(kb_p1.inline_keyboard) == 6
    assert "✅" in kb_p1.inline_keyboard[0][0].text
    assert kb_p1.inline_keyboard[0][0].callback_data == "dead:toggle:9:1"
    assert "⬜" in kb_p1.inline_keyboard[1][0].text
    assert kb_p1.inline_keyboard[1][0].callback_data == "dead:toggle:10:1"

    # Navigation row: Prev is page 0, counter
    nav_row_p1 = kb_p1.inline_keyboard[2]
    assert len(nav_row_p1) == 2
    assert nav_row_p1[0].callback_data == "dead:page:0"
    assert "2 / 2" in nav_row_p1[1].text
    assert nav_row_p1[1].callback_data == "dead:noop"


def test_dead_leave_confirm_keyboard_structure():
    """Test 1-click confirmation keyboard options: confirm and cancel."""
    kb = get_dead_leave_confirm_kb(dead_count=8, lang="ru")
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].callback_data == "dead:confirm_leave"
    assert "8" in kb.inline_keyboard[0][0].text
    assert kb.inline_keyboard[1][0].callback_data == "dead:cancel"


@pytest.mark.parametrize("lang", ["ru", "kk", "en"])
def test_dead_leave_localization_all_languages(lang: str):
    """Test all required localization strings are present and formatted for all languages."""
    btn_text = i18n.get_text("btn_leave_dead_channels", lang=lang, count=12)
    assert "12" in btn_text
    assert "💣" in btn_text

    choice_prompt = i18n.get_text("dead_choice_prompt", lang=lang, count=12)
    assert "12" in choice_prompt

    fast_btn = i18n.get_text("btn_dead_all_fast", lang=lang, count=12)
    assert "12" in fast_btn
    assert "⚡" in fast_btn

    browse_btn = i18n.get_text("btn_dead_browse_manual", lang=lang)
    assert "📋" in browse_btn

    browse_title = i18n.get_text(
        "dead_browse_title", lang=lang, page=1, total_pages=3, selected=5, total=24
    )
    assert "1" in browse_title
    assert "3" in browse_title
    assert "5" in browse_title
    assert "24" in browse_title

    select_page_btn = i18n.get_text("btn_dead_select_page", lang=lang)
    assert len(select_page_btn) > 0

    deselect_page_btn = i18n.get_text("btn_dead_deselect_page", lang=lang)
    assert len(deselect_page_btn) > 0

    delete_sel_btn = i18n.get_text("btn_dead_delete_selected", lang=lang, count=7)
    assert "7" in delete_sel_btn
    assert "🗑" in delete_sel_btn

    none_sel_alert = i18n.get_text("dead_none_selected_alert", lang=lang)
    assert len(none_sel_alert) > 0

    confirm_btn = i18n.get_text("btn_confirm_leave_dead", lang=lang, count=12)
    assert "12" in confirm_btn

    warn_prompt = i18n.get_text("dead_leave_prompt_warn", lang=lang, count=12)
    assert "12" in warn_prompt
    assert "⚠️" in warn_prompt

    start_msg = i18n.get_text("dead_leave_starting", lang=lang)
    assert "💣" in start_msg

    progress_msg = i18n.get_text(
        "dead_leave_progress", lang=lang, current=3, total=10, title="TestChannel"
    )
    assert "3" in progress_msg
    assert "10" in progress_msg
    assert "TestChannel" in progress_msg

    completed_msg = i18n.get_text("dead_leave_completed", lang=lang, count=12)
    assert "12" in completed_msg
    assert "🎉" in completed_msg


# --- 3. Bot Handlers Integration Tests ---


@pytest.mark.asyncio
async def test_cb_dead_leave_prompt_handler(sample_mixed_dialogs):
    """Test cb_dead_leave_prompt shows choice keyboard with eligible dead count."""
    mock_cb = AsyncMock()
    mock_cb.from_user.id = 12345
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {"session_id": "sess_123"}

    mock_redis = AsyncMock()

    scan_result = ScanResult(
        session_id="sess_123",
        scanned_at=datetime.now(UTC),
        total_dialogs=len(sample_mixed_dialogs),
        total_unread=100,
        dead_count=1,
        zombie_count=1,
        dialogs=sample_mixed_dialogs,
    )

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss_cls.return_value = mock_ss

        await cb_dead_leave_prompt(mock_cb, mock_state, redis=mock_redis, lang="ru")

        mock_cb.message.edit_text.assert_awaited_once()
        text_arg = mock_cb.message.edit_text.call_args[0][0]
        # Channels and groups that are dead/zombie = 2 (101 and 102)
        assert "2" in text_arg
        reply_markup = mock_cb.message.edit_text.call_args[1]["reply_markup"]
        all_cb_data = [btn.callback_data for row in reply_markup.inline_keyboard for btn in row]
        assert any("dead:all_prompt" in data for data in all_cb_data)
        assert any("dead:browse:0" in data for data in all_cb_data)


@pytest.mark.asyncio
async def test_cb_dead_all_prompt_handler(sample_mixed_dialogs):
    """Test cb_dead_all_prompt shows 1-click warning screen with confirm keyboard."""
    mock_cb = AsyncMock()
    mock_cb.from_user.id = 12345
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {"session_id": "sess_123"}

    mock_redis = AsyncMock()

    scan_result = ScanResult(
        session_id="sess_123",
        scanned_at=datetime.now(UTC),
        total_dialogs=len(sample_mixed_dialogs),
        total_unread=100,
        dead_count=5,
        zombie_count=3,
        dialogs=sample_mixed_dialogs,
    )

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss_cls.return_value = mock_ss

        await cb_dead_all_prompt(mock_cb, mock_state, redis=mock_redis, lang="ru")

        mock_cb.message.edit_text.assert_awaited_once()
        text_arg = mock_cb.message.edit_text.call_args[0][0]
        assert "8" in text_arg  # dead_count 5 + zombie_count 3
        assert "⚠️" in text_arg
        reply_markup = mock_cb.message.edit_text.call_args[1]["reply_markup"]
        assert reply_markup.inline_keyboard[0][0].callback_data == "dead:confirm_leave"


@pytest.mark.asyncio
async def test_cb_dead_browse_handler(sample_mixed_dialogs):
    """Test entering interactive browser: sets state and defaults all dead channels to selected."""
    mock_cb = AsyncMock()
    mock_cb.data = "dead:browse:0"
    mock_cb.from_user.id = 12345
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {"session_id": "sess_123"}  # no selected_dead_ids yet

    mock_redis = AsyncMock()

    scan_result = ScanResult(
        session_id="sess_123",
        scanned_at=datetime.now(UTC),
        total_dialogs=len(sample_mixed_dialogs),
        total_unread=100,
        dead_count=1,
        zombie_count=1,
        dialogs=sample_mixed_dialogs,
    )

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss_cls.return_value = mock_ss

        await cb_dead_browse(mock_cb, mock_state, redis=mock_redis, lang="ru")

        mock_state.set_state.assert_awaited_once_with(AppSG.browsing_dead_channels)
        mock_state.update_data.assert_awaited_once()
        saved_data = mock_state.update_data.call_args[1]["selected_dead_ids"]
        assert set(saved_data) == {101, 102}

        mock_cb.message.edit_text.assert_awaited_once()
        text_arg = mock_cb.message.edit_text.call_args[0][0]
        assert "2" in text_arg


@pytest.mark.asyncio
async def test_cb_dead_toggle_handler(sample_mixed_dialogs):
    """Test toggling a channel on/off updates state and refreshes view."""
    mock_cb = AsyncMock()
    mock_cb.data = "dead:toggle:101:0"
    mock_cb.from_user.id = 12345
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    # Initially both 101 and 102 are selected
    mock_state.get_data.return_value = {
        "session_id": "sess_123",
        "selected_dead_ids": [101, 102],
    }

    mock_redis = AsyncMock()

    scan_result = ScanResult(
        session_id="sess_123",
        scanned_at=datetime.now(UTC),
        total_dialogs=len(sample_mixed_dialogs),
        total_unread=100,
        dead_count=1,
        zombie_count=1,
        dialogs=sample_mixed_dialogs,
    )

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss_cls.return_value = mock_ss

        # Toggle 101 -> should remove it
        await cb_dead_toggle(mock_cb, mock_state, redis=mock_redis, lang="ru")

        mock_state.update_data.assert_awaited_once_with(selected_dead_ids=[102])
        mock_cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_dead_page_handler(sample_mixed_dialogs):
    """Test switching page in browser."""
    mock_cb = AsyncMock()
    mock_cb.data = "dead:page:0"
    mock_cb.from_user.id = 12345
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {
        "session_id": "sess_123",
        "selected_dead_ids": [101],
    }

    mock_redis = AsyncMock()

    scan_result = ScanResult(
        session_id="sess_123",
        scanned_at=datetime.now(UTC),
        total_dialogs=len(sample_mixed_dialogs),
        total_unread=100,
        dead_count=1,
        zombie_count=1,
        dialogs=sample_mixed_dialogs,
    )

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss_cls.return_value = mock_ss

        await cb_dead_page(mock_cb, mock_state, redis=mock_redis, lang="ru")
        mock_cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_dead_page_bulk_selection_handler():
    """Test bulk select_page and deselect_page actions."""
    now = datetime.now(UTC)
    dialogs = [
        DialogInfo(
            id=i,
            title=f"Channel {i}",
            type=ChatType.CHANNEL,
            status=ChatStatus.DEAD,
            last_message_date=now,
        )
        for i in range(1, 11)  # 10 dialogs
    ]

    mock_redis = AsyncMock()
    scan_result = ScanResult(
        session_id="sess_123",
        scanned_at=now,
        total_dialogs=10,
        total_unread=0,
        dead_count=10,
        zombie_count=0,
        dialogs=dialogs,
    )

    # 1. Select page 0
    mock_cb = AsyncMock()
    mock_cb.data = "dead:select_page:0"
    mock_cb.from_user.id = 12345
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {
        "session_id": "sess_123",
        "selected_dead_ids": [],
    }

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss_cls.return_value = mock_ss

        await cb_dead_page_bulk_selection(mock_cb, mock_state, redis=mock_redis, lang="ru")
        mock_state.update_data.assert_awaited_once()
        new_selected = set(mock_state.update_data.call_args[1]["selected_dead_ids"])
        # Page 0 has dialogs 1..8
        assert new_selected == set(range(1, 9))

    # 2. Deselect page 0
    mock_cb.data = "dead:deselect_page:0"
    mock_state.update_data.reset_mock()
    mock_state.get_data.return_value = {
        "session_id": "sess_123",
        "selected_dead_ids": list(range(1, 11)),
    }

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss_cls.return_value = mock_ss

        await cb_dead_page_bulk_selection(mock_cb, mock_state, redis=mock_redis, lang="ru")
        mock_state.update_data.assert_awaited_once()
        new_selected = set(mock_state.update_data.call_args[1]["selected_dead_ids"])
        # Page 0 (1..8) removed, leaving only 9 and 10
        assert new_selected == {9, 10}


@pytest.mark.asyncio
async def test_cb_dead_confirm_selected_empty_shows_alert():
    """Test clicking confirm_selected when nothing is selected alerts the user."""
    mock_cb = AsyncMock()
    mock_cb.from_user.id = 12345
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {
        "session_id": "sess_123",
        "selected_dead_ids": [],
    }

    mock_redis = AsyncMock()

    await cb_dead_confirm_selected(mock_cb, mock_state, redis=mock_redis, lang="ru")
    mock_cb.answer.assert_awaited_once()
    assert mock_cb.answer.call_args[1]["show_alert"] is True


@pytest.mark.asyncio
async def test_cb_dead_confirm_selected_executes_only_selected(sample_mixed_dialogs):
    """Test selective leave executes cleaner on selected_ids only and updates cache."""
    mock_cb = AsyncMock()
    mock_cb.from_user.id = 12345
    mock_status_msg = AsyncMock()
    mock_status_msg.edit_text = AsyncMock()
    mock_cb.message.answer.return_value = mock_status_msg
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    # Only select channel 101, excluding group 102
    mock_state.get_data.return_value = {
        "session_id": "sess_123",
        "selected_dead_ids": [101],
    }

    mock_redis = AsyncMock()
    mock_client = AsyncMock()

    scan_result = ScanResult(
        session_id="sess_123",
        scanned_at=datetime.now(UTC),
        total_dialogs=len(sample_mixed_dialogs),
        total_unread=67,
        dead_count=1,
        zombie_count=1,
        dialogs=sample_mixed_dialogs,
    )

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
        patch(
            "app.bot.handlers.ScannerService.save_scan_result",
            new_callable=AsyncMock,
        ) as mock_save_scan,
        patch("app.bot.handlers.CleanerService") as mock_cs_cls,
        patch("app.bot.handlers.RedisLock") as mock_lock_cls,
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss.load.return_value = mock_client
        mock_ss_cls.return_value = mock_ss

        mock_lock = AsyncMock()
        mock_lock.__aenter__.return_value = True
        mock_lock.__aexit__.return_value = None
        mock_lock_cls.return_value = mock_lock

        mock_cleaner = AsyncMock()
        mock_cleaner._populate_entity_cache = AsyncMock(return_value={})
        mock_cleaner.mass_leave_dead_channels = AsyncMock(return_value=1)
        mock_cs_cls.return_value = mock_cleaner

        await cb_dead_confirm_selected(mock_cb, mock_state, redis=mock_redis, lang="ru")

        mock_cleaner.mass_leave_dead_channels.assert_awaited_once()
        assert mock_cleaner.mass_leave_dead_channels.call_args[1]["selected_ids"] == {101}

        mock_save_scan.assert_awaited_once()
        saved_scan = mock_save_scan.call_args[0][1]
        remaining_ids = {d.id for d in saved_scan.dialogs}
        # 101 was removed
        assert 101 not in remaining_ids
        # 102 was NOT selected, so it remains!
        assert 102 in remaining_ids
        # Personal chat 104 is also preserved
        assert 104 in remaining_ids

        mock_status_msg.edit_text.assert_awaited()
        final_text = mock_status_msg.edit_text.call_args[0][0]
        assert "1" in final_text
        assert "🎉" in final_text


@pytest.mark.asyncio
async def test_cb_dead_cancel_handler():
    """Test cb_dead_cancel restores diagnostic report view."""
    mock_cb = AsyncMock()
    mock_cb.from_user.id = 12345
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {"session_id": "sess_123"}

    mock_redis = AsyncMock()

    scan_result = ScanResult(
        session_id="sess_123",
        scanned_at=datetime.now(UTC),
        total_dialogs=20,
        total_unread=40,
        dead_count=2,
        zombie_count=1,
    )

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss_cls.return_value = mock_ss

        await cb_dead_cancel(mock_cb, mock_state, redis=mock_redis, lang="ru")

        mock_cb.message.edit_text.assert_awaited_once()
        text_arg = mock_cb.message.edit_text.call_args[0][0]
        assert "40" in text_arg
        assert "3" in text_arg


@pytest.mark.asyncio
async def test_cb_dead_confirm_leave_handler(sample_mixed_dialogs):
    """Test mass leave on all dead channels and updates scan in Redis."""
    mock_cb = AsyncMock()
    mock_cb.from_user.id = 12345
    mock_status_msg = AsyncMock()
    mock_status_msg.edit_text = AsyncMock()
    mock_cb.message.answer.return_value = mock_status_msg
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {"session_id": "sess_123"}

    mock_redis = AsyncMock()
    mock_client = AsyncMock()

    scan_result = ScanResult(
        session_id="sess_123",
        scanned_at=datetime.now(UTC),
        total_dialogs=len(sample_mixed_dialogs),
        total_unread=67,
        dead_count=1,
        zombie_count=1,
        dialogs=sample_mixed_dialogs,
    )

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.ScannerService.get_cached_scan", return_value=scan_result),
        patch(
            "app.bot.handlers.ScannerService.save_scan_result",
            new_callable=AsyncMock,
        ) as mock_save_scan,
        patch("app.bot.handlers.CleanerService") as mock_cs_cls,
        patch("app.bot.handlers.RedisLock") as mock_lock_cls,
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss.load.return_value = mock_client
        mock_ss_cls.return_value = mock_ss

        mock_lock = AsyncMock()
        mock_lock.__aenter__.return_value = True
        mock_lock.__aexit__.return_value = None
        mock_lock_cls.return_value = mock_lock

        mock_cleaner = AsyncMock()
        mock_cleaner._populate_entity_cache = AsyncMock(return_value={})
        mock_cleaner.mass_leave_dead_channels = AsyncMock(return_value=2)
        mock_cs_cls.return_value = mock_cleaner

        await cb_dead_confirm_leave(mock_cb, mock_state, redis=mock_redis, lang="ru")

        mock_cleaner.mass_leave_dead_channels.assert_awaited_once()
        assert mock_cleaner.mass_leave_dead_channels.call_args[1]["selected_ids"] is None
        mock_save_scan.assert_awaited_once()
        saved_scan = mock_save_scan.call_args[0][1]
        # Channels and groups that were dead/zombie are removed
        remaining_ids = {d.id for d in saved_scan.dialogs}
        assert 101 not in remaining_ids
        assert 102 not in remaining_ids
        # Personal user chat is preserved
        assert 104 in remaining_ids
        assert saved_scan.zombie_count == 0
        assert saved_scan.dead_count == 1  # personal chat remains

        mock_status_msg.edit_text.assert_awaited()
        final_text = mock_status_msg.edit_text.call_args[0][0]
        assert "2" in final_text
        assert "🎉" in final_text
