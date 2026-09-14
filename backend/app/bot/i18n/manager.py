"""
I18nManager: handles localization retrieval, fallback logic,
and user language persistence in Redis.
"""
import logging

from redis.asyncio import Redis

from app.bot.i18n.translations import ARCHETYPES, TRANSLATIONS, SupportedLanguage

logger = logging.getLogger(__name__)


class I18nManager:
    """Manages translation retrieval and user language preferences."""

    @staticmethod
    def get_text(key: str, lang: str = "ru", **kwargs: object) -> str:
        """
        Return localized string for the specified key and language.
        Falls back to 'ru' if missing, then to the key itself.
        Supports formatting via kwargs.
        """
        catalog = TRANSLATIONS.get(key)
        if not catalog:
            return key

        template = catalog.get(lang) or catalog.get("ru") or key
        if kwargs:
            try:
                return template.format(**kwargs)
            except Exception as e:
                logger.debug("Formatting error for key '%s': %s", key, e)
                return template
        return template

    @staticmethod
    def get_archetype_info(archetype_key: str, lang: str = "ru") -> tuple[str, str]:
        """Return (title, description) for an archetype in the chosen language."""
        data = ARCHETYPES.get(archetype_key, ARCHETYPES["digital_monk"])
        title = data["title"].get(lang) or data["title"].get("ru") or ""
        desc = data["description"].get(lang) or data["description"].get("ru") or ""
        return title, desc

    @staticmethod
    async def set_user_language(redis: Redis, user_id: int, lang: str) -> None:
        """Persist user language choice in Redis."""
        valid_lang = (
            lang
            if lang in (SupportedLanguage.KK, SupportedLanguage.EN)
            else SupportedLanguage.RU
        )
        key = f"user_lang:{user_id}"
        # Store preference for 30 days
        await redis.setex(key, 86400 * 30, valid_lang)
        logger.info("Language for user %d set to '%s'", user_id, valid_lang)

    @staticmethod
    async def get_user_language(
        redis: Redis | None,
        user_id: int,
        tg_lang_code: str | None = None,
    ) -> str:
        """
        Resolve user's language:
        1. Check user preference in Redis
        2. Auto-detect from Telegram language code
        3. Fallback to default ('ru')
        """
        if redis:
            try:
                raw = await redis.get(f"user_lang:{user_id}")
                if raw:
                    cached = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                    if cached in ("ru", "kk", "en"):
                        return cached
            except Exception as e:
                logger.debug("Error reading language from Redis: %s", e)

        # Fallback to Telegram client language_code
        if tg_lang_code:
            code = tg_lang_code.lower()
            if code.startswith(("kk", "kz")):
                return SupportedLanguage.KK
            if code.startswith("ru"):
                return SupportedLanguage.RU
            return SupportedLanguage.EN

        return SupportedLanguage.RU


i18n = I18nManager()
