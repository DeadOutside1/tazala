"""
Internationalization (i18n) package for Tazala.
Supports Kazakh (kk), Russian (ru), English (en).
"""
from app.bot.i18n.manager import I18nManager, i18n
from app.bot.i18n.middleware import LanguageMiddleware
from app.bot.i18n.translations import SupportedLanguage

__all__ = ["I18nManager", "LanguageMiddleware", "SupportedLanguage", "i18n"]
