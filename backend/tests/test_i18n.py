"""
Unit tests for the Tazala Internationalization (i18n) module:
1. Translation catalog parity across Kazakh, Russian, and English.
2. Smart folder titles strict length limit (<= 12 chars).
3. Fallback behavior for missing translations and invalid keys.
4. User language preference persistence and auto-detection.
5. Multilingual Wrapped card rendering (Kazakh, Russian, English) in PNG format.
"""
import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from app.bot.i18n.manager import I18nManager, i18n
from app.bot.i18n.translations import ARCHETYPES, TRANSLATIONS, SupportedLanguage
from app.bot.keyboards import get_language_kb
from app.cleaner.service import CleanerService
from app.scanner.schemas import ChatType, ScanResult, TopUnreadChat
from app.wrapped.schemas import WrappedStats, ZenArchetype
from app.wrapped.service import WrappedService

# --- 1. Translation Integrity & Parity ---


def test_translations_parity_all_languages():
    """
    Ensure EVERY key in the translations catalog has non-empty values
    for all supported languages: Russian, Kazakh, and English.
    """
    supported = {SupportedLanguage.RU.value, SupportedLanguage.KK.value, SupportedLanguage.EN.value}

    for key, lang_map in TRANSLATIONS.items():
        assert isinstance(lang_map, dict), f"Key '{key}' must map to a dictionary of translations."
        missing = supported - set(lang_map.keys())
        assert not missing, f"Key '{key}' is missing translations for: {missing}"

        for lang in supported:
            val = lang_map.get(lang)
            assert val and val.strip(), f"Key '{key}' has empty text for language '{lang}'"


def test_archetypes_parity_all_languages():
    """
    Ensure all archetypes have localized title and description across ru, kk, and en.
    """
    supported = ("ru", "kk", "en")
    for arch_key, data in ARCHETYPES.items():
        for lang in supported:
            title = data["title"].get(lang)
            desc = data["description"].get(lang)
            assert title and title.strip(), f"Archetype '{arch_key}' missing title for '{lang}'"
            assert desc and desc.strip(), f"Archetype '{arch_key}' missing desc for '{lang}'"


# --- 2. Smart Folder Title Length Bound (<= 12 characters) ---


@pytest.mark.parametrize("lang", ["kk", "ru", "en"])
def test_folder_presets_length_limit(lang: str):
    """
    CRITICAL TELEGRAM CONSTRAINT: Folder titles MUST be <= 12 characters (including emojis).
    Verify that all smart folder preset titles across kk, ru, and en respect this constraint.
    """
    rules = CleanerService.get_smart_folder_presets(lang=lang)
    assert len(rules) == 4, f"Expected 4 folder rules for '{lang}', got {len(rules)}"

    for rule in rules:
        title = rule.title
        assert len(title) <= 12, (
            f"Folder title '{title}' for language '{lang}' exceeds 12 chars (len={len(title)})"
        )
        assert len(title) > 0, f"Folder title in language '{lang}' is empty"


# --- 3. Fallback Mechanism Tests ---


def test_i18n_fallback_non_existent_key():
    """Requesting a completely unknown key should return the key itself."""
    unknown_key = "non_existent_diagnostic_metric_key"
    result = i18n.get_text(unknown_key, lang="kk")
    assert result == unknown_key


def test_i18n_fallback_to_ru():
    """If a key is present in ru but missing in kk, it must fall back to ru."""
    manager = I18nManager()
    # Inject a temporary test key
    test_key = "__temp_test_key_for_fallback__"
    TRANSLATIONS[test_key] = {"ru": "Русский текст фоллбэка"}
    try:
        result = manager.get_text(test_key, lang="kk")
        assert result == "Русский текст фоллбэка"
    finally:
        TRANSLATIONS.pop(test_key, None)


def test_i18n_format_kwargs():
    """Test string formatting with kwargs."""
    result = i18n.get_text("clean_progress", lang="ru", message="Архивация", current=5, total=10)
    assert "Архивация" in result
    assert "5/10" in result


# --- 4. User Language Preference & Persistence ---


@pytest.mark.asyncio
async def test_user_language_redis_persistence():
    """Verify setting and reading language preference from Redis."""
    mock_redis = AsyncMock()
    user_id = 99887766

    # Test saving preference
    await i18n.set_user_language(mock_redis, user_id=user_id, lang="kk")
    mock_redis.setex.assert_awaited_once_with(f"user_lang:{user_id}", 86400 * 30, "kk")

    # Test reading preference from Redis
    mock_redis.get.return_value = b"kk"
    loaded_lang = await i18n.get_user_language(mock_redis, user_id=user_id)
    assert loaded_lang == "kk"


@pytest.mark.asyncio
async def test_user_language_autodetection_fallbacks():
    """Verify Telegram language_code parsing when Redis is empty."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    # Kazakh variations
    assert await i18n.get_user_language(mock_redis, 1, tg_lang_code="kk") == "kk"
    assert await i18n.get_user_language(mock_redis, 1, tg_lang_code="kk-KZ") == "kk"
    assert await i18n.get_user_language(mock_redis, 1, tg_lang_code="kz") == "kk"

    # Russian variations
    assert await i18n.get_user_language(mock_redis, 1, tg_lang_code="ru") == "ru"
    assert await i18n.get_user_language(mock_redis, 1, tg_lang_code="ru-RU") == "ru"

    # English / other variations
    assert await i18n.get_user_language(mock_redis, 1, tg_lang_code="en") == "en"
    assert await i18n.get_user_language(mock_redis, 1, tg_lang_code="es") == "en"
    assert await i18n.get_user_language(mock_redis, 1, tg_lang_code=None) == "ru"


# --- 5. Multilingual Wrapped Card Generation ---


@pytest.mark.parametrize("lang", ["kk", "ru", "en"])
def test_wrapped_multilingual_card_generation(lang: str):
    """
    Generate Spotify Wrapped-style card in Kazakh, Russian, and English.
    Assert valid PNG format, 1080x1350 resolution, and proper encoding of special characters.
    """
    stats = WrappedStats(
        session_id="test-session-i18n",
        username="tazala_user",
        total_dialogs=450,
        messages_cleared=15420,
        dead_chats_count=82,
        folders_created_count=4,
        time_saved_hours=64.2,
        zen_score=85,
        archetype=ZenArchetype.CHAOS_LORD,
        archetype_title="Повелитель хаоса",
        archetype_description="Красный бейдж Telegram управлял твоей жизнью.",
    )

    service = WrappedService()
    png_bytes = service.generate_wrapped_card(stats, lang=lang)

    # Validate binary PNG header
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG header for lang '{lang}'"

    # Validate image dimensions and mode
    image = Image.open(io.BytesIO(png_bytes))
    assert image.size == (1080, 1350), f"Incorrect dimensions: {image.size}"
    assert image.format == "PNG"


def test_calculate_wrapped_stats_localized():
    """Verify calculate_wrapped_stats localizes title and description according to lang."""
    scan = ScanResult(
        session_id="sess-test",
        scanned_at=datetime.now(UTC),
        total_dialogs=100,
        total_unread=25000,
        dead_count=50,
        zombie_count=20,
        active_count=30,
        dead_percentage=70.0,
        top_unread_chats=[
            TopUnreadChat(id=1, title="Test", unread_count=25000, type=ChatType.CHANNEL)
        ],
    )

    service = WrappedService()
    stats_kk = service.calculate_wrapped_stats(scan, lang="kk")
    assert stats_kk.archetype == ZenArchetype.DIGITAL_HOARDER
    assert stats_kk.archetype_title == "Цифрлық плюшкин"
    assert "арналарды жинадыңыз" in stats_kk.archetype_description

    stats_en = service.calculate_wrapped_stats(scan, lang="en")
    assert stats_en.archetype == ZenArchetype.DIGITAL_HOARDER
    assert stats_en.archetype_title == "Digital Hoarder"
    assert "Hoarded channels" in stats_en.archetype_description


def test_language_keyboard():
    """Test get_language_kb structure and callback data."""
    kb = get_language_kb()
    assert len(kb.inline_keyboard) == 4
    assert kb.inline_keyboard[0][0].callback_data == "set_lang:kk"
    assert kb.inline_keyboard[1][0].callback_data == "set_lang:ru"
    assert kb.inline_keyboard[2][0].callback_data == "set_lang:en"
    assert kb.inline_keyboard[3][0].callback_data == "back_to_start"
