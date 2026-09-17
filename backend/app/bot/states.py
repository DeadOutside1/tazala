"""
FSM States for Tazala Telegram Bot workflow.
"""
from aiogram.fsm.state import State, StatesGroup


class AuthSG(StatesGroup):
    """Authentication state group."""

    waiting_qr_scan = State()
    waiting_2fa_password = State()
    waiting_phone_number = State()
    waiting_sms_code = State()


class AppSG(StatesGroup):
    """Main workflow state group."""

    authenticated = State()
    scanning = State()
    ready_to_clean = State()
    selecting_folders = State()
    cleaning = State()


class FeedbackSG(StatesGroup):
    """User rating and review state group."""

    waiting_rating = State()
    waiting_comment = State()


class FolderManagerSG(StatesGroup):
    """Telegram folder manager state group."""

    viewing_list = State()
    viewing_folder = State()
    waiting_rename_input = State()
    confirm_delete = State()


