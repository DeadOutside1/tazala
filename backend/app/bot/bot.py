"""
Bot and Dispatcher initialization and lifecycle factory.
"""
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from redis.asyncio import Redis

from app.bot.handlers import router as bot_router
from app.bot.i18n.middleware import LanguageMiddleware
from app.config import settings

logger = logging.getLogger(__name__)


async def setup_bot_commands(bot: Bot) -> None:
    """Register bot commands in Telegram to show native [Menu] button."""
    try:
        # Default commands
        await bot.set_my_commands(
            commands=[
                BotCommand(command="start", description="🏠 Главное меню / Start"),
                BotCommand(command="menu", description="📱 Меню функций"),
                BotCommand(command="scan", description="🔍 Диагностика завала"),
                BotCommand(command="clean", description="🧹 Очистка и смарт-папки"),
                BotCommand(command="lang", description="🌐 Сменить язык / Тіл"),
                BotCommand(command="help", description="🔒 Безопасность"),
            ],
            scope=BotCommandScopeDefault(),
        )
        # Russian
        await bot.set_my_commands(
            commands=[
                BotCommand(command="start", description="🏠 Главное меню"),
                BotCommand(command="menu", description="📱 Меню функций"),
                BotCommand(command="scan", description="🔍 Диагностика завала"),
                BotCommand(command="clean", description="🧹 Очистка и смарт-папки"),
                BotCommand(command="lang", description="🌐 Сменить язык"),
                BotCommand(command="help", description="🔒 Безопасность и помощь"),
            ],
            scope=BotCommandScopeDefault(),
            language_code="ru",
        )
        # Kazakh
        await bot.set_my_commands(
            commands=[
                BotCommand(command="start", description="🏠 Басты мәзір"),
                BotCommand(command="menu", description="📱 Функциялар мәзірі"),
                BotCommand(command="scan", description="🔍 Завал диагностикасы"),
                BotCommand(command="clean", description="🧹 Тазарту және папкалар"),
                BotCommand(command="lang", description="🌐 Тілді ауыстыру"),
                BotCommand(command="help", description="🔒 Қауіпсіздік және анықтама"),
            ],
            scope=BotCommandScopeDefault(),
            language_code="kk",
        )
        # English
        await bot.set_my_commands(
            commands=[
                BotCommand(command="start", description="🏠 Main menu"),
                BotCommand(command="menu", description="📱 Feature menu"),
                BotCommand(command="scan", description="🔍 Clutter diagnostics"),
                BotCommand(command="clean", description="🧹 Cleanup and smart folders"),
                BotCommand(command="lang", description="🌐 Change language"),
                BotCommand(command="help", description="🔒 Security and help"),
            ],
            scope=BotCommandScopeDefault(),
            language_code="en",
        )
        logger.info("Bot commands and [Menu] button registered successfully.")
    except Exception as e:
        logger.warning("Failed setting bot commands: %s", e)


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

