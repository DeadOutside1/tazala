"""
Unit tests for Tazala Telegram Bot UI:
- Keyboards structure & callback data
- ThrottledMessageEditor rate limiting & error handling
- /start command handler workflow
- Logout callback and session destruction
- Bot & Dispatcher initialization factory
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.bot import create_bot_and_dispatcher
from app.bot.handlers import (
    _format_code_slots,
    cb_session_logout,
    cmd_admin_stats,
    cmd_start,
)
from app.bot.keyboards import (
    get_admin_kb,
    get_clean_completed_kb,
    get_diagnostic_kb,
    get_feedback_rating_kb,
    get_scan_kb,
    get_skip_comment_kb,
    get_sms_code_kb,
    get_start_kb,
    get_wrapped_kb,
)
from app.bot.utils import ThrottledMessageEditor
from app.config import settings

# --- 1. Keyboard Tests ---


def test_sms_code_numpad_keyboard_structure():
    """Test get_sms_code_kb contains numpad digits, del, clear, and action buttons."""
    kb = get_sms_code_kb()
    # Check 7 rows: 1-3, 4-6, 7-9, del-0-clear, resend, switch_qr, main_menu
    assert len(kb.inline_keyboard) == 7
    assert kb.inline_keyboard[0][0].callback_data == "num:1"
    assert kb.inline_keyboard[0][1].callback_data == "num:2"
    assert kb.inline_keyboard[0][2].callback_data == "num:3"
    assert kb.inline_keyboard[3][0].callback_data == "num:del"
    assert kb.inline_keyboard[3][1].callback_data == "num:0"
    assert kb.inline_keyboard[3][2].callback_data == "num:clear"
    assert kb.inline_keyboard[4][0].callback_data == "resend_sms_code"
    assert kb.inline_keyboard[5][0].callback_data == "start_auth"
    assert kb.inline_keyboard[6][0].callback_data == "back_to_start"


def test_format_code_slots():
    """Test _format_code_slots formats partial and full 5-digit codes."""
    empty = _format_code_slots("")
    assert empty == "`[ • ]` `[ • ]` `[ • ]` `[ • ]` `[ • ]`"

    partial = _format_code_slots("48")
    assert partial == "`[ 4 ]` `[ 8 ]` `[ • ]` `[ • ]` `[ • ]`"

    full = _format_code_slots("48291")
    assert full == "`[ 4 ]` `[ 8 ]` `[ 2 ]` `[ 9 ]` `[ 1 ]`"


def test_start_keyboard_structure():
    """
    Test get_start_kb contains auth, folder manager, feedback,
    security, and language selection buttons.
    """
    kb = get_start_kb()
    assert len(kb.inline_keyboard) == 6
    assert kb.inline_keyboard[0][0].callback_data == "start_auth"
    assert kb.inline_keyboard[1][0].callback_data == "start_phone_auth"
    assert kb.inline_keyboard[2][0].callback_data == "folder_mgr:list"
    assert kb.inline_keyboard[3][0].callback_data == "leave_feedback"
    assert kb.inline_keyboard[4][0].callback_data == "about_security"
    assert kb.inline_keyboard[5][0].callback_data == "choose_lang"




def test_scan_keyboard_structure():
    """Test get_scan_kb contains run_scan and back_to_start buttons."""
    kb = get_scan_kb()
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].callback_data == "run_scan"
    assert kb.inline_keyboard[1][0].callback_data == "back_to_start"


def test_diagnostic_keyboard_structure():
    """Test get_diagnostic_kb renders options with unread count and back_to_start."""
    kb = get_diagnostic_kb(unread_count=350)
    assert len(kb.inline_keyboard) == 5
    assert kb.inline_keyboard[0][0].callback_data == "run_clean:all"
    assert "350" in kb.inline_keyboard[0][0].text
    assert kb.inline_keyboard[1][0].callback_data == "run_clean:read_only"
    assert kb.inline_keyboard[2][0].callback_data == "run_clean:folders_only"
    assert kb.inline_keyboard[3][0].callback_data == "session_logout"
    assert kb.inline_keyboard[4][0].callback_data == "back_to_start"


def test_wrapped_keyboard_structure():
    """Test get_wrapped_kb contains share URL, leave_feedback, and back_to_start."""
    kb = get_wrapped_kb(session_id="dummy-sess")
    assert len(kb.inline_keyboard) == 3
    assert "https://t.me/share/url" in (kb.inline_keyboard[0][0].url or "")
    assert kb.inline_keyboard[1][0].callback_data == "leave_feedback"
    assert kb.inline_keyboard[2][0].callback_data == "back_to_start"


def test_clean_completed_keyboard_structure():
    """Test get_clean_completed_kb contains all required action buttons."""
    kb = get_clean_completed_kb()
    assert len(kb.inline_keyboard) == 5
    assert kb.inline_keyboard[0][0].callback_data == "run_clean:folders_only"
    assert kb.inline_keyboard[1][0].callback_data == "run_scan"
    assert kb.inline_keyboard[2][0].callback_data == "leave_feedback"
    assert kb.inline_keyboard[3][0].callback_data == "session_logout"
    assert kb.inline_keyboard[4][0].callback_data == "back_to_start"


def test_start_keyboard_active_session():
    """Test get_start_kb displays active session buttons when has_active_session=True."""
    kb = get_start_kb(has_active_session=True)
    assert len(kb.inline_keyboard) == 7
    assert kb.inline_keyboard[0][0].callback_data == "run_scan"
    assert kb.inline_keyboard[1][0].callback_data == "run_clean:folders_only"
    assert kb.inline_keyboard[2][0].callback_data == "folder_mgr:list"
    assert kb.inline_keyboard[3][0].callback_data == "leave_feedback"
    assert kb.inline_keyboard[4][0].callback_data == "session_logout"


def test_start_keyboard_admin_visibility():
    """Test get_start_kb shows admin button only when is_admin is True."""
    user_kb = get_start_kb(is_admin=False)
    user_buttons = [btn.callback_data for row in user_kb.inline_keyboard for btn in row]
    assert "admin_panel" not in user_buttons

    admin_kb = get_start_kb(is_admin=True)
    admin_buttons = [btn.callback_data for row in admin_kb.inline_keyboard for btn in row]
    assert "admin_panel" in admin_buttons


def test_feedback_rating_keyboard_structure():
    """Test get_feedback_rating_kb has 5 star ratings and a back button."""
    kb = get_feedback_rating_kb()
    assert len(kb.inline_keyboard) == 2
    assert len(kb.inline_keyboard[0]) == 5
    for i in range(1, 6):
        assert kb.inline_keyboard[0][i - 1].callback_data == f"rate_star:{i}"
    assert kb.inline_keyboard[1][0].callback_data == "back_to_start"


def test_skip_comment_keyboard_structure():
    """Test get_skip_comment_kb contains skip comment and main menu buttons."""
    kb = get_skip_comment_kb()
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].callback_data == "skip_comment"
    assert kb.inline_keyboard[1][0].callback_data == "back_to_start"


def test_admin_keyboard_structure():
    """Test get_admin_kb has refresh stats, reviews, and back buttons."""
    kb = get_admin_kb()
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].callback_data == "admin_refresh"
    assert kb.inline_keyboard[0][1].callback_data == "admin_reviews"
    assert kb.inline_keyboard[1][0].callback_data == "back_to_start"




# --- 2. ThrottledMessageEditor Tests ---


@pytest.mark.asyncio
async def test_throttled_message_editor_rate_limiting():
    """Test message editor throttles rapid updates unless forced."""
    mock_msg = AsyncMock(spec=Message)
    mock_msg.edit_text = AsyncMock()

    editor = ThrottledMessageEditor(mock_msg, min_interval=1.0)

    # First update: executes immediately
    first_res = await editor.edit_text_safe("Update 1")
    assert first_res is True
    assert mock_msg.edit_text.await_count == 1

    # Immediate second update: throttled
    second_res = await editor.edit_text_safe("Update 2")
    assert second_res is False
    assert mock_msg.edit_text.await_count == 1

    # Forced update: executes despite interval
    forced_res = await editor.edit_text_safe("Update Forced", force=True)
    assert forced_res is True
    assert mock_msg.edit_text.await_count == 2


@pytest.mark.asyncio
async def test_throttled_message_editor_error_handling():
    """Test editor handles TelegramBadRequest and TelegramRetryAfter without crashing."""
    mock_msg = AsyncMock(spec=Message)

    # Simulate 'message is not modified' error
    mock_msg.edit_text = AsyncMock(
        side_effect=TelegramBadRequest(method=MagicMock(), message="message is not modified")
    )
    editor = ThrottledMessageEditor(mock_msg, min_interval=0.0)

    res = await editor.edit_text_safe("Same text", force=True)
    assert res is False

    # Simulate Flood / RetryAfter error
    mock_msg.edit_text = AsyncMock(
        side_effect=TelegramRetryAfter(method=MagicMock(), message="Flood", retry_after=5)
    )
    res_retry = await editor.edit_text_safe("Flood text", force=True)
    assert res_retry is False


# --- 3. /start Command Handler Test ---


@pytest.mark.asyncio
async def test_cmd_start():
    """Test /start clears state and sends welcome message with start keyboard."""
    mock_msg = AsyncMock(spec=Message)
    mock_msg.answer = AsyncMock()
    mock_msg.from_user = None

    mock_state = AsyncMock(spec=FSMContext)
    mock_state.clear = AsyncMock()
    mock_state.get_data = AsyncMock(return_value={})

    mock_redis = AsyncMock()

    await cmd_start(mock_msg, mock_state, redis=mock_redis)

    mock_state.clear.assert_awaited_once()
    mock_msg.answer.assert_awaited_once()
    args, kwargs = mock_msg.answer.await_args
    assert "Добро пожаловать в Tazala!" in args[0]
    assert kwargs.get("reply_markup") is not None


# --- 4. Session Logout Callback Test ---


@pytest.mark.asyncio
async def test_cb_session_logout():
    """Test logout callback destroys session in store and resets state."""
    mock_cb = AsyncMock(spec=CallbackQuery)
    mock_cb.data = "session_logout"
    mock_cb.answer = AsyncMock()
    mock_cb.from_user = None
    mock_cb.message = AsyncMock(spec=Message)
    mock_cb.message.answer = AsyncMock()

    mock_state = AsyncMock(spec=FSMContext)
    mock_state.get_data = AsyncMock(return_value={"session_id": "test-logout-session"})
    mock_state.clear = AsyncMock()

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    with patch("app.bot.handlers.SessionStore") as mock_store_cls:
        mock_instance = AsyncMock()
        mock_instance.exists = AsyncMock(return_value=True)
        mock_instance.load = AsyncMock(return_value=AsyncMock())
        mock_instance.destroy = AsyncMock()
        mock_store_cls.return_value = mock_instance

        await cb_session_logout(mock_cb, mock_state, redis=mock_redis)

    mock_state.clear.assert_awaited_once()
    mock_instance.destroy.assert_awaited_once()
    assert mock_cb.message.answer.await_count == 1
    call_text = mock_cb.message.answer.await_args[0][0]
    assert "Сессия успешно уничтожена" in call_text


@pytest.mark.asyncio
async def test_cb_session_logout_with_wrapped_card():
    """Test logout callback sends photo card when cleanup stats are present."""
    mock_cb = AsyncMock(spec=CallbackQuery)
    mock_cb.data = "session_logout"
    mock_cb.answer = AsyncMock()
    mock_cb.from_user = None
    mock_cb.message = AsyncMock(spec=Message)
    mock_cb.message.answer_photo = AsyncMock()

    mock_state = AsyncMock(spec=FSMContext)
    mock_state.get_data = AsyncMock(return_value={"session_id": "test-logout-session"})
    mock_state.clear = AsyncMock()

    mock_redis = AsyncMock()
    stats_json = (
        '{"session_id":"test-logout-session","total_dialogs":50,"total_unread":100,'
        '"messages_cleared":100,"time_saved_hours":1.5,"zen_score":95,'
        '"archetype":"digital_monk","archetype_title":"Цифровой монах",'
        '"archetype_description":"Абсолютный дзен","top_unread_source":"News"}'
    )
    mock_redis.get = AsyncMock(return_value=stats_json)

    with patch("app.bot.handlers.SessionStore") as mock_store_cls, \
         patch("app.bot.handlers.WrappedService.generate_wrapped_card", return_value=b"fake_png"):
        mock_instance = AsyncMock()
        mock_instance.exists = AsyncMock(return_value=True)
        mock_instance.load = AsyncMock(return_value=AsyncMock())
        mock_instance.destroy = AsyncMock()
        mock_store_cls.return_value = mock_instance

        await cb_session_logout(mock_cb, mock_state, redis=mock_redis)

    mock_state.clear.assert_awaited_once()
    mock_instance.destroy.assert_awaited_once()
    assert mock_cb.message.answer_photo.await_count == 1
    call_kwargs = mock_cb.message.answer_photo.await_args.kwargs
    assert "Сессия успешно уничтожена" in call_kwargs.get("caption", "")



# --- 5. Bot & Dispatcher Factory Test ---


def test_create_bot_and_dispatcher_empty_token():
    """Test factory returns (None, None) gracefully when token is unset."""
    with patch.object(settings, "TELEGRAM_BOT_TOKEN", ""):
        bot, dp = create_bot_and_dispatcher()
        assert bot is None
        assert dp is None


def test_create_bot_and_dispatcher_with_token():
    """Test factory creates Bot and Dispatcher when valid token is provided."""
    dummy_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
    with patch.object(settings, "TELEGRAM_BOT_TOKEN", dummy_token):
        bot, dp = create_bot_and_dispatcher()
        assert bot is not None
        assert dp is not None
        asyncio.run(bot.session.close())


# --- 6. Admin Access Control Tests ---


@pytest.mark.asyncio
async def test_cmd_admin_stats_access_denied_for_non_admin():
    """Test non-admin user receives access denied message."""
    mock_msg = AsyncMock(spec=Message)
    mock_msg.from_user = MagicMock(id=999999999)  # Not in admin_ids
    mock_msg.answer = AsyncMock()

    with patch.object(settings, "ADMIN_USER_IDS", "8041783822"):
        await cmd_admin_stats(mock_msg)

    mock_msg.answer.assert_awaited_once()
    called_text = mock_msg.answer.await_args[0][0]
    assert "Доступ запрещен" in called_text


@pytest.mark.asyncio
async def test_cmd_admin_stats_allowed_for_admin():
    """Test authorized admin receives formatted dashboard."""
    mock_msg = AsyncMock(spec=Message)
    mock_msg.from_user = MagicMock(id=8041783822)  # Authorized admin
    mock_msg.answer = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.scard.return_value = 5
    mock_redis.hgetall.return_value = {}

    with patch.object(settings, "ADMIN_USER_IDS", "8041783822"):
        await cmd_admin_stats(mock_msg, redis=mock_redis)

    mock_msg.answer.assert_awaited_once()
    called_text = mock_msg.answer.await_args[0][0]
    assert "Tazala Admin Dashboard" in called_text

