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
from app.bot.handlers import cb_session_logout, cmd_start
from app.bot.keyboards import (
    get_diagnostic_kb,
    get_scan_kb,
    get_start_kb,
    get_wrapped_kb,
)
from app.bot.utils import ThrottledMessageEditor
from app.config import settings

# --- 1. Keyboard Tests ---


def test_start_keyboard_structure():
    """Test get_start_kb contains auth, security, and language selection buttons."""
    kb = get_start_kb()
    assert len(kb.inline_keyboard) == 4
    assert kb.inline_keyboard[0][0].callback_data == "start_auth"
    assert kb.inline_keyboard[1][0].callback_data == "start_phone_auth"
    assert kb.inline_keyboard[2][0].callback_data == "about_security"
    assert kb.inline_keyboard[3][0].callback_data == "choose_lang"



def test_scan_keyboard_structure():
    """Test get_scan_kb contains run_scan callback."""
    kb = get_scan_kb()
    assert len(kb.inline_keyboard) == 1
    assert kb.inline_keyboard[0][0].callback_data == "run_scan"


def test_diagnostic_keyboard_structure():
    """Test get_diagnostic_kb renders options with unread count."""
    kb = get_diagnostic_kb(unread_count=350)
    assert len(kb.inline_keyboard) == 4
    assert kb.inline_keyboard[0][0].callback_data == "run_clean:all"
    assert "350" in kb.inline_keyboard[0][0].text
    assert kb.inline_keyboard[1][0].callback_data == "run_clean:read_only"
    assert kb.inline_keyboard[2][0].callback_data == "run_clean:folders_only"
    assert kb.inline_keyboard[3][0].callback_data == "session_logout"


def test_wrapped_keyboard_structure():
    """Test get_wrapped_kb contains share URL and logout callback."""
    kb = get_wrapped_kb(session_id="dummy-sess")
    assert len(kb.inline_keyboard) == 2
    assert "https://t.me/share/url" in (kb.inline_keyboard[0][0].url or "")
    assert kb.inline_keyboard[1][0].callback_data == "session_logout"


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

    mock_state = AsyncMock(spec=FSMContext)
    mock_state.clear = AsyncMock()

    await cmd_start(mock_msg, mock_state)

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
    mock_cb.message = AsyncMock(spec=Message)
    mock_cb.message.answer = AsyncMock()

    mock_state = AsyncMock(spec=FSMContext)
    mock_state.get_data = AsyncMock(return_value={"session_id": "test-logout-session"})
    mock_state.clear = AsyncMock()

    mock_redis = AsyncMock()

    with patch("app.bot.handlers.SessionStore") as mock_store_cls:
        mock_instance = AsyncMock()
        mock_instance.load = AsyncMock(return_value=AsyncMock())
        mock_instance.destroy = AsyncMock()
        mock_store_cls.return_value = mock_instance

        await cb_session_logout(mock_cb, mock_state, redis=mock_redis)

    mock_state.clear.assert_awaited_once()
    mock_instance.destroy.assert_awaited_once()
    assert mock_cb.message.answer.await_count == 1
    call_text = mock_cb.message.answer.await_args[0][0]
    assert "Сессия успешно уничтожена" in call_text


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
