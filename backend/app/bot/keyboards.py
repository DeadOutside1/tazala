"""
Inline keyboards for Tazala Bot UI.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_kb() -> InlineKeyboardMarkup:
    """Initial menu keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔑 Войти по QR-коду",
                    callback_data="start_auth",
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ О безопасности (Zero-Knowledge)",
                    callback_data="about_security",
                )
            ],
        ]
    )


def get_scan_kb() -> InlineKeyboardMarkup:
    """Action button to trigger account diagnostics."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔍 Запустить диагностику аккаунта",
                    callback_data="run_scan",
                )
            ]
        ]
    )


def get_diagnostic_kb(unread_count: int) -> InlineKeyboardMarkup:
    """Action buttons after diagnostic results."""
    clean_all_text = f"🧹 Навести Дзен ({unread_count} непрочитанных + папки)"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=clean_all_text,
                    callback_data="run_clean:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Только сбросить непрочитанные",
                    callback_data="run_clean:read_only",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📁 Только создать смарт-папки",
                    callback_data="run_clean:folders_only",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Выйти и удалить сессию",
                    callback_data="session_logout",
                )
            ],
        ]
    )


def get_wrapped_kb(session_id: str) -> InlineKeyboardMarkup:
    """Actions after cleanup completion: sharing & session destruction."""
    share_url = "https://t.me/share/url?url=Я%20навел%20Дзен%20в%20Telegram%20с%20Tazala!"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📲 Поделиться в Stories / Чатах",
                    url=share_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Уничтожить сессию (Zero-Knowledge)",
                    callback_data="session_logout",
                )
            ],
        ]
    )
