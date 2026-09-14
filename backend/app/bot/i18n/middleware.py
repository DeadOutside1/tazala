"""
Aiogram middleware for automatic user language detection and injection into handler context.
"""
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from app.bot.i18n.manager import i18n


class LanguageMiddleware(BaseMiddleware):
    """Detects and injects 'lang' and translation helper '_' into event data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if not user:
            user = getattr(event, "from_user", None)

        redis = data.get("redis")
        if user:
            lang = await i18n.get_user_language(
                redis=redis,
                user_id=user.id,
                tg_lang_code=user.language_code,
            )
        else:
            lang = "ru"

        data["lang"] = lang
        data["_"] = lambda key, **kwargs: i18n.get_text(key, lang=lang, **kwargs)

        return await handler(event, data)
