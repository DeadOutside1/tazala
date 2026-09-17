"""
Unit and integration tests for Nuclear Button (Mass Leave Dead/Zombie Channels):
- mass_leave_dead_channels logic (filtering DEAD & ZOMBIE channels/groups only)
- ignoring personal chats (ChatType.USER)
- error tolerance / resilience on individual chat failures
- keyboard structures for diagnostic prompt & confirmation
- localization in RU, KK, EN
- bot callback handlers (prompt, cancel, confirm_leave)
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.bot.handlers import cb_dead_cancel, cb_dead_confirm_leave, cb_dead_leave_prompt
from app.bot.i18n.manager import i18n
from app.bot.keyboards import get_dead_leave_confirm_kb, get_diagnostic_kb
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


def test_dead_leave_confirm_keyboard_structure():
    """Test confirmation keyboard options: confirm and cancel."""
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
async def test_cb_dead_leave_prompt_handler():
    """Test cb_dead_leave_prompt shows confirmation keyboard with total dead count."""
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
        total_dialogs=50,
        total_unread=100,
        dead_count=5,
        zombie_count=3,
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
        assert "8" in text_arg  # 5 dead + 3 zombie
        assert "⚠️" in text_arg


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
    """Test cb_dead_confirm_leave executes mass leave and updates scan in Redis."""
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
