"""
Multilingual inline keyboards for Tazala Bot UI.
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.bot.i18n.manager import i18n
from app.cleaner.schemas import FolderRule


def get_main_menu_reply_kb(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Persistent bottom reply keyboard for quick access to main features."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=i18n.get_text("menu_btn_main", lang=lang)),
                KeyboardButton(text=i18n.get_text("menu_btn_scan", lang=lang)),
            ],
            [
                KeyboardButton(text=i18n.get_text("menu_btn_lang", lang=lang)),
                KeyboardButton(text=i18n.get_text("menu_btn_help", lang=lang)),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_language_kb() -> InlineKeyboardMarkup:
    """Keyboard for selecting bot interface language."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="set_lang:kk")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en")],
            [InlineKeyboardButton(text="⬅️ Артқа / Назад / Back", callback_data="back_to_start")],
        ]
    )


def get_start_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Initial menu keyboard localized to user language."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_start_auth", lang=lang),
                    callback_data="start_auth",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_phone_auth", lang=lang),
                    callback_data="start_phone_auth",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_security", lang=lang),
                    callback_data="about_security",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_choose_lang", lang=lang),
                    callback_data="choose_lang",
                )
            ],
        ]
    )


def get_phone_auth_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Navigation keyboard while entering phone number."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_switch_to_qr", lang=lang),
                    callback_data="start_auth",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_main_menu", lang=lang),
                    callback_data="back_to_start",
                )
            ],
        ]
    )


def get_sms_code_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Navigation keyboard while waiting for verification code."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_resend_code", lang=lang),
                    callback_data="resend_sms_code",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_switch_to_qr", lang=lang),
                    callback_data="start_auth",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_main_menu", lang=lang),
                    callback_data="back_to_start",
                )
            ],
        ]
    )


def get_scan_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Action button to trigger account diagnostics."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_run_scan", lang=lang),
                    callback_data="run_scan",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_main_menu", lang=lang),
                    callback_data="back_to_start",
                )
            ],
        ]
    )


def get_diagnostic_kb(unread_count: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """Action buttons for cleaning choices localized."""
    clean_all_text = i18n.get_text("btn_clean_all", lang=lang, unread=unread_count)
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
                    text=i18n.get_text("btn_clean_read_only", lang=lang),
                    callback_data="run_clean:read_only",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_clean_folders_only", lang=lang),
                    callback_data="run_clean:folders_only",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_logout", lang=lang),
                    callback_data="session_logout",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_main_menu", lang=lang),
                    callback_data="back_to_start",
                )
            ],
        ]
    )


def get_folder_selection_kb(
    available_folders: list[FolderRule],
    selected_emojis: set[str],
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """Interactive checkbox keyboard for folder category selection."""
    rows: list[list[InlineKeyboardButton]] = []

    for rule in available_folders:
        check = "✅" if rule.emoji in selected_emojis else "⬜"
        rows.append([
            InlineKeyboardButton(
                text=f"{check} {rule.title}",
                callback_data=f"toggle_folder:{rule.emoji}",
            )
        ])

    # Select all / Deselect all
    rows.append([
        InlineKeyboardButton(
            text=i18n.get_text("btn_select_all_folders", lang=lang),
            callback_data="select_all_folders",
        ),
        InlineKeyboardButton(
            text=i18n.get_text("btn_deselect_all_folders", lang=lang),
            callback_data="deselect_all_folders",
        ),
    ])

    # Confirm button
    rows.append([
        InlineKeyboardButton(
            text=i18n.get_text("btn_confirm_folders", lang=lang),
            callback_data="confirm_folders",
        )
    ])

    # Back button
    rows.append([
        InlineKeyboardButton(
            text=i18n.get_text("btn_back", lang=lang),
            callback_data="back_to_diagnostic",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_wrapped_kb(session_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Actions after cleanup completion: sharing & session destruction."""
    share_text = (
        "Мен%20Tazala%20арқылы%20Telegram-ды%20тазарттым!"
        if lang == "kk"
        else (
            "I%20achieved%20Zen%20in%20Telegram%20with%20Tazala!"
            if lang == "en"
            else "Я%20навел%20Дзен%20в%20Telegram%20с%20Tazala!"
        )
    )
    share_url = f"https://t.me/share/url?url={share_text}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_share", lang=lang),
                    url=share_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_logout", lang=lang),
                    callback_data="session_logout",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_main_menu", lang=lang),
                    callback_data="back_to_start",
                )
            ],
        ]
    )
