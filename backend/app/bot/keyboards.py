"""
Multilingual inline keyboards for Tazala Bot UI.
"""
from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.bot.i18n.manager import i18n
from app.cleaner.schemas import FolderRule, UserFolderInfo


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


def get_start_kb(
    lang: str = "ru",
    has_active_session: bool = False,
    is_admin: bool = False,
) -> InlineKeyboardMarkup:
    """
    Initial menu keyboard localized to user language.
    Displays active session options if user is already logged in.
    Displays admin panel button if user is an authorized admin.
    """
    rows: list[list[InlineKeyboardButton]] = []

    if is_admin:
        rows.append([
            InlineKeyboardButton(
                text=i18n.get_text("btn_admin_panel", lang=lang),
                callback_data="admin_panel",
            )
        ])

    if has_active_session:
        rows.extend([
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_continue_session", lang=lang),
                    callback_data="run_scan",
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
                    text=i18n.get_text("btn_folder_manager", lang=lang),
                    callback_data="folder_mgr:list",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_leave_feedback", lang=lang),
                    callback_data="leave_feedback",
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
        ])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    rows.extend([
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
                text=i18n.get_text("btn_folder_manager", lang=lang),
                callback_data="folder_mgr:list",
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n.get_text("btn_leave_feedback", lang=lang),
                callback_data="leave_feedback",
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
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)



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
    """
    Interactive number pad keyboard for entering verification code without sending
    chat text (which prevents Telegram from intercepting and auto-invalidating the code).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="num:1"),
                InlineKeyboardButton(text="2", callback_data="num:2"),
                InlineKeyboardButton(text="3", callback_data="num:3"),
            ],
            [
                InlineKeyboardButton(text="4", callback_data="num:4"),
                InlineKeyboardButton(text="5", callback_data="num:5"),
                InlineKeyboardButton(text="6", callback_data="num:6"),
            ],
            [
                InlineKeyboardButton(text="7", callback_data="num:7"),
                InlineKeyboardButton(text="8", callback_data="num:8"),
                InlineKeyboardButton(text="9", callback_data="num:9"),
            ],
            [
                InlineKeyboardButton(text="⌫", callback_data="num:del"),
                InlineKeyboardButton(text="0", callback_data="num:0"),
                InlineKeyboardButton(text="🗑", callback_data="num:clear"),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_resend_code", lang=lang),
                    callback_data="resend_sms_code",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_switch_to_qr", lang=lang),
                    callback_data="start_auth",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_main_menu", lang=lang),
                    callback_data="back_to_start",
                ),
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


def get_diagnostic_kb(
    unread_count: int, dead_count: int = 0, lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Action buttons for cleaning choices localized."""
    clean_all_text = i18n.get_text("btn_clean_all", lang=lang, unread=unread_count)
    buttons = [
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
    ]
    if dead_count > 0:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_leave_dead_channels", lang=lang, count=dead_count),
                    callback_data="dead:leave_prompt",
                )
            ]
        )
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_folder_manager", lang=lang),
                    callback_data="folder_mgr:list",
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
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dead_leave_confirm_kb(dead_count: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """Confirmation keyboard for mass unsubscribe from dead/zombie channels."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_confirm_leave_dead", lang=lang, count=dead_count),
                    callback_data="dead:confirm_leave",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_cancel", lang=lang),
                    callback_data="dead:cancel",
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


def get_clean_completed_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard shown after cleanup completion while session remains active."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_clean_folders_only", lang=lang),
                    callback_data="run_clean:folders_only",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_folder_manager", lang=lang),
                    callback_data="folder_mgr:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_rescan", lang=lang),
                    callback_data="run_scan",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_leave_feedback", lang=lang),
                    callback_data="leave_feedback",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_logout", lang=lang),
                    callback_data="session_logout",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_main_menu", lang=lang),
                    callback_data="back_to_start",
                ),
            ],
        ]
    )


def get_wrapped_kb(session_id: str = "", lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Actions after cleanup & logout:
    sharing results across Telegram, WhatsApp, Stories & return to start.
    """
    bot_url = "https://t.me/tazala_app_bot"
    share_text = (
        "Мен%20Tazala%20арқылы%20Telegram-ды%20тазалап%2C%20Дзенге%20жеттім!%20Сен%20де%20көріп%20көр%3A"
        if lang == "kk"
        else (
            "I%20achieved%20Zen%20in%20Telegram%20with%20Tazala!%20Try%20it%20too%3A"
            if lang == "en"
            else "Я%20навел%20Дзен%20в%20Telegram%20с%20Tazala!%20Попробуй%20и%20ты%3A"
        )
    )
    tg_share_url = f"https://t.me/share/url?url={bot_url}&text={share_text}"
    wa_share_url = f"https://api.whatsapp.com/send?text={share_text}%20{bot_url}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_share_tg", lang=lang),
                    url=tg_share_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_share_whatsapp", lang=lang),
                    url=wa_share_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_share_stories", lang=lang),
                    callback_data=f"wrapped:stories_guide:{session_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_leave_feedback", lang=lang),
                    callback_data="leave_feedback",
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


def get_wrapped_stories_guide_kb(
    session_id: str = "",
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """Action buttons for posting Wrapped card to Instagram and Telegram Stories."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_copy_bot_link", lang=lang),
                    copy_text=CopyTextButton(text="https://t.me/tazala_app_bot"),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_open_instagram", lang=lang),
                    url="https://instagram.com",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_back_to_card", lang=lang),
                    callback_data=f"wrapped:back:{session_id}",
                )
            ],
        ]
    )


def get_feedback_rating_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard with 1 to 5 star ratings."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 1", callback_data="rate_star:1"),
                InlineKeyboardButton(text="⭐ 2", callback_data="rate_star:2"),
                InlineKeyboardButton(text="⭐ 3", callback_data="rate_star:3"),
                InlineKeyboardButton(text="⭐ 4", callback_data="rate_star:4"),
                InlineKeyboardButton(text="⭐ 5", callback_data="rate_star:5"),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_back", lang=lang),
                    callback_data="back_to_start",
                )
            ],
        ]
    )


def get_skip_comment_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard allowing user to skip optional text comment."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_skip_comment", lang=lang),
                    callback_data="skip_comment",
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


def get_admin_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Admin dashboard actions keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_refresh_stats", lang=lang),
                    callback_data="admin_refresh",
                ),
                InlineKeyboardButton(
                    text=i18n.get_text("btn_recent_reviews", lang=lang),
                    callback_data="admin_reviews",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_main_menu", lang=lang),
                    callback_data="back_to_start",
                )
            ],
        ]
    )


def get_folders_list_kb(
    folders: list[UserFolderInfo],
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """Keyboard displaying list of all user Telegram folders and action buttons."""
    rows: list[list[InlineKeyboardButton]] = []
    for f in folders:
        rows.append([
            InlineKeyboardButton(
                text=f"📂 {f.title} ({f.chats_count})",
                callback_data=f"folder_mgr:view:{f.id}",
            )
        ])

    rows.append([
        InlineKeyboardButton(
            text=i18n.get_text("btn_add_smart_folder", lang=lang),
            callback_data="folder_mgr:add_preset",
        ),
        InlineKeyboardButton(
            text=i18n.get_text("btn_main_menu", lang=lang),
            callback_data="back_to_start",
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_folder_actions_kb(
    folder_id: int,
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """Actions for a specific folder: rename, delete, back."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_rename_folder", lang=lang),
                    callback_data=f"folder_mgr:rename:{folder_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_delete_folder", lang=lang),
                    callback_data=f"folder_mgr:delete_prompt:{folder_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_back_to_folders", lang=lang),
                    callback_data="folder_mgr:list",
                )
            ],
        ]
    )


def get_folder_delete_confirm_kb(
    folder_id: int,
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """Confirmation prompt before deleting a dialog folder."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_confirm_delete", lang=lang),
                    callback_data=f"folder_mgr:confirm_delete:{folder_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_cancel", lang=lang),
                    callback_data=f"folder_mgr:view:{folder_id}",
                )
            ],
        ]
    )


