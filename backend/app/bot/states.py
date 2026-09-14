"""
FSM States for Tazala Telegram Bot workflow.
"""
from aiogram.fsm.state import State, StatesGroup


class AuthSG(StatesGroup):
    """Authentication state group."""

    waiting_qr_scan = State()
    waiting_2fa_password = State()


class AppSG(StatesGroup):
    """Main workflow state group."""

    authenticated = State()
    scanning = State()
    ready_to_clean = State()
    cleaning = State()
