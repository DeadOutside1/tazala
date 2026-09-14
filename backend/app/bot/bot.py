"""
Bot and Dispatcher initialization and lifecycle factory.
"""
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from redis.asyncio import Redis

from app.bot.handlers import router as bot_router
from app.bot.i18n.middleware import LanguageMiddleware
from app.config import settings

logger = logging.getLogger(__name__)


def create_bot_and_dispatcher(
    redis: Redis | None = None,
) -> tuple[Bot, Dispatcher] | tuple[None, None]:
    """
    Instantiate Bot and Dispatcher with registered handlers and storage.
    If TELEGRAM_BOT_TOKEN is missing or blank, returns (None, None) safely.
    """
    token = settings.TELEGRAM_BOT_TOKEN.strip()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured; skipping Telegram bot startup.")
        return None, None

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())
    if redis is not None:
        dp["redis"] = redis

    # Register i18n middleware
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    dp.include_router(bot_router)
    logger.info("Telegram Bot and Dispatcher initialized successfully.")
    return bot, dp

