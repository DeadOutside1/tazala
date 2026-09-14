"""
Utility helpers for Telegram bot message throttling and safe edits.
"""
import asyncio
import logging

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)


class ThrottledMessageEditor:
    """Safely updates Telegram messages without hitting rate limits."""

    def __init__(self, message: Message, min_interval: float = 1.5) -> None:
        self.message = message
        self.min_interval = min_interval
        self.last_edit_time: float = 0.0

    async def edit_text_safe(
        self,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        force: bool = False,
    ) -> bool:
        """
        Edit message text safely. If called too frequently, skips update unless force=True.
        Returns True if message was successfully updated, False otherwise.
        """
        now = asyncio.get_running_loop().time()
        if not force and (now - self.last_edit_time < self.min_interval):
            return False

        try:
            await self.message.edit_text(text, reply_markup=reply_markup)
            self.last_edit_time = asyncio.get_running_loop().time()
            return True
        except TelegramRetryAfter as err:
            logger.warning("Telegram flood wait on edit: sleeping %ds", err.retry_after)
            return False
        except TelegramBadRequest as err:
            if "message is not modified" in str(err).lower():
                return False
            logger.debug("TelegramBadRequest while editing: %s", err)
            return False
        except Exception as err:
            logger.debug("Unexpected error while editing message: %s", err)
            return False
