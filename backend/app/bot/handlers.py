"""
Aiogram 3 handlers implementing the complete Tazala interactive detox workflow.
"""
import asyncio
import logging
import uuid

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from redis.asyncio import Redis

from app.auth.schemas import AuthState
from app.auth.service import QRAuthService
from app.bot.keyboards import (
    get_diagnostic_kb,
    get_scan_kb,
    get_start_kb,
    get_wrapped_kb,
)
from app.bot.states import AppSG, AuthSG
from app.bot.utils import ThrottledMessageEditor
from app.cleaner.schemas import CleanConfig
from app.cleaner.service import CleanerService
from app.config import settings
from app.scanner.service import ScannerService
from app.telegram.client_manager import ClientManager
from app.telegram.session_store import SessionStore
from app.wrapped.service import WrappedService

logger = logging.getLogger(__name__)

router = Router(name="bot_router")

# Map of active in-flight login clients (session_id -> TelegramClient)
_ACTIVE_AUTH_CLIENTS: dict[str, object] = {}


def _get_redis(redis_instance: Redis | None = None) -> Redis:
    """Helper to return provided Redis or connect to settings.REDIS_URL."""
    if redis_instance is not None:
        return redis_instance
    return Redis.from_url(settings.REDIS_URL, decode_responses=False)


# --- A. /start & /help Handlers ---


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Welcome user and explain Tazala mission."""
    await state.clear()
    text = (
        "🧘 **Добро пожаловать в Tazala!**\n\n"
        "Твой персональный инструмент для **инфо-детокса в Telegram**:\n"
        "• 🧹 Сброс 100k+ непрочитанных за секунды\n"
        "• 📁 Автоматическая сортировка по смарт-папкам\n"
        "• 🎁 Вирусная Wrapped-карточка в стиле Spotify\n"
        "• 🔒 **Zero-Knowledge**: вход через QR, сессия уничтожается сразу после очистки\n\n"
        "Нажмите кнопку ниже, чтобы начать очистку!"
    )
    await message.answer(text, reply_markup=get_start_kb(), parse_mode="Markdown")


# --- B. About Security ---


@router.callback_query(F.data == "about_security")
async def cb_about_security(callback: CallbackQuery) -> None:
    """Provide transparent details on Zero-Knowledge security."""
    text = (
        "🔒 **Как устроена безопасность в Tazala:**\n\n"
        "1. **Вход по QR-коду:** Никаких паролей и номеров телефонов.\n"
        "2. **Оперативная память (RAM):** Строка сессии хранится исключительно в Redis "
        "с TTL 5 минут. Ни одного байта не записывается на диск.\n"
        "3. **Физическое уничтожение:** Сразу после очистки вызывается `log_out()`, "
        "что отзывает ключ авторизации на серверах самого Telegram.\n"
        "4. **Open Source:** Весь код открыт для аудита: "
        "https://github.com/DeadOutside1/tazala\n\n"
        "Готовы навести порядок?"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Войти по QR-коду", callback_data="start_auth")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_start")],
        ]
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "back_to_start")
async def cb_back_to_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to start menu."""
    await state.clear()
    text = (
        "🧘 **Tazala — Инфо-детокс Telegram**\n\n"
        "Очистите свой мессенджер от информационного шума:"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_start_kb(), parse_mode="Markdown")
    await callback.answer()


# --- C. QR Authentication Flow ---


@router.callback_query(F.data == "start_auth")
async def cb_start_auth(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
) -> None:
    """Initiate Telethon QR login flow."""
    session_id = str(uuid.uuid4())
    await state.set_state(AuthSG.waiting_qr_scan)
    await state.update_data(session_id=session_id)

    r = _get_redis(redis)
    session_store = SessionStore(r)
    auth_service = QRAuthService(session_store=session_store)

    client = ClientManager.create_ephemeral_client()
    await client.connect()
    _ACTIVE_AUTH_CLIENTS[session_id] = client

    if callback.message:
        status_msg = await callback.message.answer("⏳ Генерация защищенного QR-кода...")
    else:
        status_msg = None
    await callback.answer()

    qr_message: Message | None = None

    async def on_qr(url: str, png_bytes: bytes) -> None:
        nonlocal qr_message
        caption = (
            "📲 **Отсканируйте QR-код для входа:**\n\n"
            "1. Откройте **Telegram** на телефоне\n"
            "2. Перейдите в **Настройки ➔ Устройства ➔ Подключить устройство**\n"
            "3. Наведите камеру на этот QR-код\n\n"
            "_Код обновляется автоматически каждые 25 секунд._"
        )
        file = BufferedInputFile(png_bytes, filename="tazala_qr.png")
        if qr_message is None and callback.message:
            qr_message = await callback.message.answer_photo(
                photo=file,
                caption=caption,
                parse_mode="Markdown",
            )
            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass
        elif qr_message:
            try:
                await qr_message.edit_media(
                    media=InputMediaPhoto(media=file, caption=caption, parse_mode="Markdown")
                )
            except Exception as e:
                logger.debug("QR media edit: %s", e)

    async def on_state(auth_state: AuthState) -> None:
        if auth_state == AuthState.TWO_FA_REQUIRED:
            await state.set_state(AuthSG.waiting_2fa_password)
            if callback.message:
                await callback.message.answer(
                    "🔒 **Ваш аккаунт защищен 2FA.**\n\n"
                    "Пожалуйста, пришлите ваш облачный пароль сообщением в этот чат.\n"
                    "_(Сообщение с паролем будет немедленно удалено из чата)_",
                    parse_mode="Markdown",
                )

    async def run_auth_task():
        try:
            result = await auth_service.start_qr_login(
                client=client,
                on_qr=on_qr,
                on_state=on_state,
                session_id=session_id,
                timeout=120,
            )
            if result.state == AuthState.AUTHENTICATED:
                await state.set_state(AppSG.authenticated)
                if callback.message:
                    await callback.message.answer(
                        "✅ **Вы успешно вошли в аккаунт!**\n\n"
                        "Сессия защищена в памяти Redis. Нажмите кнопку ниже, чтобы "
                        "просканировать завал в Telegram:",
                        reply_markup=get_scan_kb(),
                        parse_mode="Markdown",
                    )
            elif result.state == AuthState.EXPIRED:
                if callback.message:
                    await callback.message.answer(
                        "⏱ Время действия QR-кода истекло. Начните заново: /start"
                    )
        except Exception as err:
            logger.exception("Auth task error: %s", err)
        finally:
            _ACTIVE_AUTH_CLIENTS.pop(session_id, None)

    asyncio.create_task(run_auth_task())


@router.message(AuthSG.waiting_2fa_password)
async def msg_2fa_password(
    message: Message,
    state: FSMContext,
    redis: Redis | None = None,
) -> None:
    """Safely receive 2FA cloud password and complete authentication."""
    password = message.text or ""
    # Security: Delete password message from chat immediately
    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    session_id = data.get("session_id", "")
    client = _ACTIVE_AUTH_CLIENTS.get(session_id)

    if not client:
        await message.answer("Сессия авторизации устарела. Пожалуйста, отправьте /start.")
        await state.clear()
        return

    r = _get_redis(redis)
    auth_service = QRAuthService(session_store=SessionStore(r))
    result = await auth_service.complete_2fa(client, password, session_id)

    if result.state == AuthState.AUTHENTICATED:
        await state.set_state(AppSG.authenticated)
        await message.answer(
            "✅ **Пароль 2FA принят!**\n\n"
            "Вы успешно вошли. Запустите диагностику цифрового завала:",
            reply_markup=get_scan_kb(),
            parse_mode="Markdown",
        )
    else:
        await message.answer(
            "❌ **Ошибка 2FA пароля.**\nПожалуйста, отправьте пароль еще раз "
            "или начните заново: /start"
        )


# --- D. Diagnostics / Scan Flow ---


@router.callback_query(F.data == "run_scan")
async def cb_run_scan(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
) -> None:
    """Execute account diagnostic scan."""
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        if callback.message:
            await callback.message.answer("Сессия не найдена. Пожалуйста, начните с /start.")
        await callback.answer()
        return

    await state.set_state(AppSG.scanning)
    status_msg = (
        await callback.message.answer("🔍 **Начинаем сканирование диалогов...**")
        if callback.message
        else None
    )
    await callback.answer()

    r = _get_redis(redis)
    session_store = SessionStore(r)
    client = await session_store.load(session_id)
    if not client:
        if status_msg:
            await status_msg.edit_text("Сессия истекла. Пожалуйста, начните с /start.")
        return

    editor = ThrottledMessageEditor(status_msg) if status_msg else None

    async def on_scan_progress(scanned: int) -> None:
        if editor:
            await editor.edit_text_safe(f"🔍 Просканировано **{scanned}** диалогов...")

    scanner = ScannerService()
    try:
        scan_result = await scanner.scan_account(
            client=client,
            session_id=session_id,
            progress_callback=on_scan_progress,
        )
        await scanner.save_scan_result(r, scan_result)

        # Build diagnostic report
        dead_total = scan_result.dead_count + scan_result.zombie_count
        top_list = "\n".join(
            f"• {chat.title[:20]}: **{chat.unread_count}** непрочит."
            for chat in scan_result.top_unread_chats[:3]
        ) or "Нет непрочитанных чатов 🎉"

        report_text = (
            "📊 **Результаты диагностики аккаунта:**\n\n"
            f"💬 Всего диалогов: **{scan_result.total_dialogs}**\n"
            f"🔴 Непрочитанных сообщений: **{scan_result.total_unread:,}**\n"
            f"🗑 Неактивных каналов/групп: **{dead_total}** ({scan_result.dead_percentage}%)\n"
            f"📁 В архиве: **{scan_result.archived_count}**\n\n"
            f"🏆 **Главные источники завала:**\n{top_list}\n\n"
            "Выберите желаемый сценарий очистки:"
        )

        await state.set_state(AppSG.ready_to_clean)
        if status_msg:
            await status_msg.edit_text(
                report_text,
                reply_markup=get_diagnostic_kb(scan_result.total_unread),
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.exception("Scan failed: %s", e)
        if status_msg:
            await status_msg.edit_text(f"❌ Ошибка сканирования: {e}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# --- E. Cleanup / Zen Button Flow ---


@router.callback_query(F.data.startswith("run_clean"))
async def cb_run_clean(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
) -> None:
    """Execute cleanup actions based on user selection."""
    action = callback.data or ""
    mark_read = "folders_only" not in action
    create_folders = "read_only" not in action

    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        if callback.message:
            await callback.message.answer("Сессия не найдена. Отправьте /start.")
        await callback.answer()
        return

    r = _get_redis(redis)
    scan_result = await ScannerService.get_cached_scan(r, session_id)
    if not scan_result:
        if callback.message:
            await callback.message.answer("Сначала выполните диагностику: /start")
        await callback.answer()
        return

    await state.set_state(AppSG.cleaning)
    status_msg = (
        await callback.message.answer("🧹 **Наводим Дзен... Начинаем очистку.**")
        if callback.message
        else None
    )
    await callback.answer()

    session_store = SessionStore(r)
    client = await session_store.load(session_id)
    if not client:
        if status_msg:
            await status_msg.edit_text("Сессия истекла. Отправьте /start.")
        return

    editor = ThrottledMessageEditor(status_msg) if status_msg else None

    async def on_clean_progress(progress) -> None:
        if editor:
            await editor.edit_text_safe(
                f"🧹 **{progress.message}** ({progress.current}/{progress.total})..."
            )

    cleaner = CleanerService()
    config = CleanConfig(
        mark_read=mark_read,
        create_folders=create_folders,
        auto_logout=False,
    )

    try:
        clean_result = await cleaner.execute_zen_clean(
            client=client,
            scan_result=scan_result,
            config=config,
            session_store=session_store,
            progress_callback=on_clean_progress,
        )

        # Generate Wrapped Stats & Card
        uname = callback.from_user.username if callback.from_user else None
        stats = WrappedService.calculate_wrapped_stats(
            scan_result, clean_result=clean_result, username=uname
        )
        await WrappedService.save_wrapped(r, stats)

        card_png = WrappedService().generate_wrapped_card(stats)
        file = BufferedInputFile(card_png, filename="tazala_wrapped.png")

        caption = (
            "🧘 **Дзен достигнут!**\n\n"
            f"Твой архетип: **{stats.archetype_title}**\n"
            f"🧹 Очищено сообщений: **{stats.messages_cleared:,}**\n"
            f"⏳ Сэкономлено: **{stats.time_saved_hours} ч.**\n"
            f"⭐ Zen Score: **{stats.zen_score} / 100**\n\n"
            "Поделитесь карточкой с друзьями или завершите сессию:"
        )

        if callback.message:
            await callback.message.answer_photo(
                photo=file,
                caption=caption,
                reply_markup=get_wrapped_kb(session_id),
                parse_mode="Markdown",
            )
            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass
    except Exception as e:
        logger.exception("Cleanup failed: %s", e)
        if status_msg:
            await status_msg.edit_text(f"❌ Ошибка очистки: {e}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# --- F. Logout Handler ---


@router.callback_query(F.data == "session_logout")
async def cb_session_logout(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
) -> None:
    """Completely destroy session and revoke keys on Telegram servers."""
    data = await state.get_data()
    session_id = data.get("session_id")
    await state.clear()

    if session_id:
        r = _get_redis(redis)
        session_store = SessionStore(r)
        client = await session_store.load(session_id)
        await session_store.destroy(session_id, client)

    text = (
        "🔒 **Сессия успешно уничтожена!**\n\n"
        "• Ключ авторизации отозван на серверах Telegram (`log_out`)\n"
        "• Временная сессия удалена из памяти Redis\n\n"
        "Ваш аккаунт в полной безопасности. Чтобы начать заново — отправьте /start."
    )
    if callback.message:
        await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()
