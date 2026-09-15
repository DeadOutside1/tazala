"""
Aiogram 3 handlers implementing the complete Tazala interactive detox workflow.
"""
import asyncio
import logging
import re
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
from app.auth.service import PhoneAuthService, QRAuthService
from app.bot.i18n.manager import i18n
from app.bot.keyboards import (
    get_diagnostic_kb,
    get_folder_selection_kb,
    get_language_kb,
    get_phone_auth_kb,
    get_scan_kb,
    get_sms_code_kb,
    get_start_kb,
    get_wrapped_kb,
)
from app.bot.states import AppSG, AuthSG
from app.bot.utils import ThrottledMessageEditor
from app.cleaner.schemas import CleanConfig
from app.cleaner.service import CleanerService, get_smart_folder_presets
from app.config import settings
from app.scanner.service import ScannerService
from app.telegram.client_manager import ClientManager
from app.telegram.lock import RedisLock
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
    return Redis.from_url(settings.REDIS_URL, decode_responses=False, protocol=2)


# --- A. /start, /help, /lang & Language Switching Handlers ---


@router.message(CommandStart())
@router.message(Command("help"))
@router.message(Command("menu"))
@router.message(
    F.text.casefold().in_({
        "menu", "меню", "мәзір", "главное меню",
        "басты мәзір", "main menu", "старт", "start",
    })
)
async def cmd_start(message: Message, state: FSMContext, lang: str = "ru") -> None:
    """Welcome user and explain Tazala mission."""
    await state.clear()
    text = i18n.get_text("start_welcome", lang=lang)
    await message.answer(text, reply_markup=get_start_kb(lang=lang), parse_mode="Markdown")


@router.message(Command("lang"))
@router.callback_query(F.data == "choose_lang")
async def cmd_choose_lang(
    event: Message | CallbackQuery,
    lang: str = "ru",
) -> None:
    """Prompt user to select interface language."""
    text = i18n.get_text("select_language", lang=lang)
    kb = get_language_kb()
    if isinstance(event, CallbackQuery):
        if event.message:
            await event.message.edit_text(text, reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
) -> None:
    """Save selected language preference in Redis and show updated start menu."""
    new_lang = callback.data.split(":", 1)[1] if callback.data else "ru"
    if new_lang not in ("ru", "kk", "en"):
        new_lang = "ru"

    user_id = callback.from_user.id if callback.from_user else 0
    r = _get_redis(redis)
    if user_id:
        await i18n.set_user_language(r, user_id, new_lang)

    confirm_text = i18n.get_text("lang_changed", lang=new_lang)
    await callback.answer(confirm_text)

    welcome_text = i18n.get_text("start_welcome", lang=new_lang)
    if callback.message:
        await callback.message.edit_text(
            f"{confirm_text}\n\n{welcome_text}",
            reply_markup=get_start_kb(lang=new_lang),
            parse_mode="Markdown",
        )


# --- B. About Security ---


@router.callback_query(F.data == "about_security")
async def cb_about_security(callback: CallbackQuery, lang: str = "ru") -> None:
    """Provide transparent details on Zero-Knowledge security."""
    text = i18n.get_text("security_info", lang=lang)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_start_auth", lang=lang),
                    callback_data="start_auth",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get_text("btn_back", lang=lang),
                    callback_data="back_to_start",
                )
            ],
        ]
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "back_to_start")
async def cb_back_to_start(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "ru",
) -> None:
    """Return to start menu."""
    await state.clear()
    text = i18n.get_text("start_welcome", lang=lang)
    if callback.message:
        await callback.message.edit_text(
            text, reply_markup=get_start_kb(lang=lang), parse_mode="Markdown"
        )
    await callback.answer()



# --- C. QR Authentication Flow ---


@router.callback_query(F.data == "start_auth")
async def cb_start_auth(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
) -> None:
    """Initiate Telethon QR login flow."""
    # Clean up previous auth client if any
    data = await state.get_data()
    prev_session_id = data.get("session_id")
    if prev_session_id and prev_session_id in _ACTIVE_AUTH_CLIENTS:
        prev_client = _ACTIVE_AUTH_CLIENTS.pop(prev_session_id, None)
        if prev_client:
            try:
                await prev_client.disconnect()
            except Exception:
                pass

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
        status_msg = await callback.message.answer(i18n.get_text("qr_generating", lang=lang))
    else:
        status_msg = None
    await callback.answer()

    qr_message: Message | None = None

    async def on_qr(url: str, png_bytes: bytes) -> None:
        nonlocal qr_message
        caption = i18n.get_text("qr_caption", lang=lang)
        file = BufferedInputFile(png_bytes, filename="tazala_qr.png")

        # Extract token from QR URL for deeplink button
        deeplink_kb = None
        token_match = re.search(r"token=([A-Za-z0-9_-]+)", url)
        if token_match:
            token = token_match.group(1)
            deeplink_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=i18n.get_text("btn_deeplink_login", lang=lang),
                            url=f"tg://login?token={token}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=i18n.get_text("btn_main_menu", lang=lang),
                            callback_data="back_to_start",
                        )
                    ],
                ]
            )

        if qr_message is None and callback.message:
            qr_message = await callback.message.answer_photo(
                photo=file,
                caption=caption,
                reply_markup=deeplink_kb,
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
                    media=InputMediaPhoto(media=file, caption=caption, parse_mode="Markdown"),
                    reply_markup=deeplink_kb,
                )
            except Exception as e:
                logger.debug("QR media edit: %s", e)

    async def on_state(auth_state: AuthState) -> None:
        if auth_state == AuthState.TWO_FA_REQUIRED:
            await state.set_state(AuthSG.waiting_2fa_password)
            if callback.message:
                await callback.message.answer(
                    i18n.get_text("two_fa_prompt", lang=lang),
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
                        i18n.get_text("qr_authenticated", lang=lang),
                        reply_markup=get_scan_kb(lang=lang),
                        parse_mode="Markdown",
                    )
            elif result.state == AuthState.EXPIRED:
                if callback.message:
                    await callback.message.answer(i18n.get_text("qr_expired", lang=lang))
        except Exception as err:
            logger.exception("Auth task error: %s", err)
        finally:
            _ACTIVE_AUTH_CLIENTS.pop(session_id, None)

    asyncio.create_task(run_auth_task())


# --- C2. Phone Number Authentication Flow ---


@router.callback_query(F.data == "start_phone_auth")
async def cb_start_phone_auth(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "ru",
) -> None:
    """Initiate phone number login flow."""
    # Clean up previous auth client if any
    data = await state.get_data()
    prev_session_id = data.get("session_id")
    if prev_session_id and prev_session_id in _ACTIVE_AUTH_CLIENTS:
        prev_client = _ACTIVE_AUTH_CLIENTS.pop(prev_session_id, None)
        if prev_client:
            try:
                await prev_client.disconnect()
            except Exception:
                pass

    session_id = str(uuid.uuid4())
    await state.set_state(AuthSG.waiting_phone_number)
    await state.update_data(session_id=session_id)

    client = ClientManager.create_ephemeral_client()
    await client.connect()
    _ACTIVE_AUTH_CLIENTS[session_id] = client

    if callback.message:
        await callback.message.answer(
            i18n.get_text("phone_prompt", lang=lang),
            reply_markup=get_phone_auth_kb(lang=lang),
            parse_mode="Markdown",
        )
    await callback.answer()


@router.message(AuthSG.waiting_phone_number)
async def msg_phone_number(
    message: Message,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
) -> None:
    """Receive phone number and send verification code."""
    raw_phone = (message.text or "").strip()
    phone = re.sub(r"[^\d+]", "", raw_phone)
    if not phone.startswith("+") and phone.isdigit():
        phone = "+" + phone

    # Basic validation: must start with + and have digits (7 to 15 digits)
    if not phone.startswith("+") or not re.match(r"^\+\d{7,15}$", phone):
        await message.answer(
            i18n.get_text("phone_invalid_format", lang=lang),
            reply_markup=get_phone_auth_kb(lang=lang),
            parse_mode="Markdown",
        )
        return

    data = await state.get_data()
    session_id = data.get("session_id", "")
    client = _ACTIVE_AUTH_CLIENTS.get(session_id)

    if not client:
        await message.answer(i18n.get_text("session_not_found", lang=lang))
        await state.clear()
        return

    r = _get_redis(redis)
    phone_auth = PhoneAuthService(session_store=SessionStore(r))

    try:
        send_res = await phone_auth.send_code(client, phone)
        phone_code_hash = send_res.phone_code_hash
        delivery_type = getattr(send_res, "delivery_type", "app")
        email_pattern = getattr(send_res, "email_pattern", None)
        await state.update_data(
            phone=phone,
            phone_code_hash=phone_code_hash,
            delivery_type=delivery_type,
        )
        await state.set_state(AuthSG.waiting_sms_code)

        prompt_key = f"sms_code_prompt_{delivery_type}"
        text_template = i18n.get_text(prompt_key, lang=lang)
        if text_template == prompt_key:
            text_template = i18n.get_text("sms_code_prompt", lang=lang)

        prompt_text = text_template.replace("{phone}", phone)
        if email_pattern and "{email}" in prompt_text:
            prompt_text = prompt_text.replace("{email}", email_pattern)

        await message.answer(
            prompt_text,
            reply_markup=get_sms_code_kb(lang=lang),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("Failed to send code to %s: %s", phone[:4], e)
        err_msg = str(e)
        if "SendCodeUnavailable" in type(e).__name__ or "options for this type" in err_msg:
            err_msg = i18n.get_text("resend_code_unavailable", lang=lang)
        await message.answer(f"❌ {err_msg}", reply_markup=get_phone_auth_kb(lang=lang))
        await state.clear()
        _ACTIVE_AUTH_CLIENTS.pop(session_id, None)
        try:
            await client.disconnect()
        except Exception:
            pass


@router.callback_query(F.data == "resend_sms_code")
async def cb_resend_sms_code(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
) -> None:
    """Resend verification code via Telegram MTProto."""
    data = await state.get_data()
    session_id = data.get("session_id", "")
    phone = data.get("phone", "")
    phone_code_hash = data.get("phone_code_hash", "")
    client = _ACTIVE_AUTH_CLIENTS.get(session_id)

    if not client or not phone or not phone_code_hash:
        await callback.answer(i18n.get_text("session_not_found", lang=lang), show_alert=True)
        return

    r = _get_redis(redis)
    phone_auth = PhoneAuthService(session_store=SessionStore(r))
    try:
        resend_res = await phone_auth.resend_code(client, phone, phone_code_hash)
        new_hash = resend_res.phone_code_hash
        delivery_type = getattr(resend_res, "delivery_type", "app")
        await state.update_data(phone_code_hash=new_hash, delivery_type=delivery_type)
        await callback.answer(i18n.get_text("code_resent_alert", lang=lang), show_alert=False)

        prompt_key = f"sms_code_prompt_{delivery_type}"
        text_template = i18n.get_text(prompt_key, lang=lang)
        if text_template == prompt_key:
            text_template = i18n.get_text("sms_code_prompt", lang=lang)
        prompt_text = text_template.replace("{phone}", phone)

        if callback.message:
            await callback.message.answer(
                f"🔄 {prompt_text}",
                reply_markup=get_sms_code_kb(lang=lang),
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.warning("Failed resending code for session %s: %s", session_id[:8], e)
        err_msg = str(e)
        if "SendCodeUnavailable" in type(e).__name__ or "options for this type" in err_msg:
            err_msg = i18n.get_text("resend_code_unavailable", lang=lang)
        await callback.answer(f"⚠️ {err_msg}", show_alert=True)


@router.message(AuthSG.waiting_sms_code)
async def msg_sms_code(
    message: Message,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
) -> None:
    """Receive SMS/Telegram code and complete sign-in."""
    raw_code = message.text or ""
    code = raw_code.strip().replace(" ", "").replace("-", "")

    # Security: Delete code message from chat
    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    session_id = data.get("session_id", "")
    phone = data.get("phone", "")
    phone_code_hash = data.get("phone_code_hash", "")
    client = _ACTIVE_AUTH_CLIENTS.get(session_id)

    if not client or not phone or not phone_code_hash:
        await message.answer(i18n.get_text("session_not_found", lang=lang))
        await state.clear()
        return

    r = _get_redis(redis)
    phone_auth = PhoneAuthService(session_store=SessionStore(r))
    result = await phone_auth.sign_in_with_code(
        client=client,
        phone=phone,
        code=code,
        phone_code_hash=phone_code_hash,
        session_id=session_id,
    )

    if result.state == AuthState.AUTHENTICATED:
        await state.set_state(AppSG.authenticated)
        _ACTIVE_AUTH_CLIENTS.pop(session_id, None)
        await message.answer(
            i18n.get_text("phone_auth_success", lang=lang),
            reply_markup=get_scan_kb(lang=lang),
            parse_mode="Markdown",
        )
    elif result.state == AuthState.TWO_FA_REQUIRED:
        await state.set_state(AuthSG.waiting_2fa_password)
        await message.answer(
            i18n.get_text("two_fa_prompt", lang=lang),
            parse_mode="Markdown",
        )
    else:
        err_msg = result.error or i18n.get_text("phone_auth_error", lang=lang)
        await message.answer(
            f"❌ **{err_msg}**",
            reply_markup=get_sms_code_kb(lang=lang),
            parse_mode="Markdown",
        )


# --- C3. 2FA Password Handler (shared for QR and Phone flows) ---


@router.message(AuthSG.waiting_2fa_password)
async def msg_2fa_password(
    message: Message,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
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
        await message.answer(i18n.get_text("session_not_found", lang=lang))
        await state.clear()
        return

    r = _get_redis(redis)
    auth_service = QRAuthService(session_store=SessionStore(r))
    result = await auth_service.complete_2fa(client, password, session_id)

    if result.state == AuthState.AUTHENTICATED:
        await state.set_state(AppSG.authenticated)
        _ACTIVE_AUTH_CLIENTS.pop(session_id, None)
        await message.answer(
            i18n.get_text("two_fa_success", lang=lang),
            reply_markup=get_scan_kb(lang=lang),
            parse_mode="Markdown",
        )
    else:
        await message.answer(i18n.get_text("two_fa_error", lang=lang))


# --- D. Diagnostics / Scan Flow ---


@router.callback_query(F.data == "run_scan")
async def cb_run_scan(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
) -> None:
    """Execute account diagnostic scan."""
    user_id = callback.from_user.id if callback.from_user else 0
    r = _get_redis(redis)

    async with RedisLock(r, f"scan:{user_id}", timeout=300) as acquired:
        if not acquired:
            await callback.answer(
                i18n.get_text("action_already_running", lang=lang),
                show_alert=True,
            )
            return

        data = await state.get_data()
        session_id = data.get("session_id")
        if not session_id:
            if callback.message:
                await callback.message.answer(i18n.get_text("session_not_found", lang=lang))
            await callback.answer()
            return

        await state.set_state(AppSG.scanning)
        status_msg = (
            await callback.message.answer(i18n.get_text("scan_starting", lang=lang))
            if callback.message
            else None
        )
        await callback.answer()

        session_store = SessionStore(r)
        client = await session_store.load(session_id)
        if not client:
            if status_msg:
                await status_msg.edit_text(i18n.get_text("session_not_found", lang=lang))
            return

        editor = ThrottledMessageEditor(status_msg) if status_msg else None

        async def on_scan_progress(scanned: int) -> None:
            if editor:
                await editor.edit_text_safe(
                    i18n.get_text("scan_progress", lang=lang, scanned=scanned)
                )

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
            unreads_label = (
                "непрочит." if lang == "ru" else "оқылмаған" if lang == "kk" else "unread"
            )
            top_list = "\n".join(
                f"• {chat.title[:20]}: **{chat.unread_count}** {unreads_label}"
                for chat in scan_result.top_unread_chats[:3]
            ) or i18n.get_text("no_unread_chats", lang=lang)

            report_text = i18n.get_text(
                "scan_report",
                lang=lang,
                total_dialogs=scan_result.total_dialogs,
                total_unread=f"{scan_result.total_unread:,}",
                dead_total=dead_total,
                dead_percentage=scan_result.dead_percentage,
                archived_count=scan_result.archived_count,
                top_list=top_list,
            )

            await state.set_state(AppSG.ready_to_clean)
            if status_msg:
                await status_msg.edit_text(
                    report_text,
                    reply_markup=get_diagnostic_kb(scan_result.total_unread, lang=lang),
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.exception("Scan failed: %s", e)
            if status_msg:
                await status_msg.edit_text(f"❌ {e}")
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass


# --- E. Folder Selection Flow ---


@router.callback_query(F.data == "run_clean:folders_only")
async def cb_run_clean_folders_only(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
) -> None:
    """Show interactive folder selection menu before creating folders."""
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        if callback.message:
            await callback.message.answer(i18n.get_text("session_not_found", lang=lang))
        await callback.answer()
        return

    r = _get_redis(redis)
    scan_result = await ScannerService.get_cached_scan(r, session_id)
    if not scan_result:
        if callback.message:
            await callback.message.answer(i18n.get_text("session_not_found", lang=lang))
        await callback.answer()
        return

    presets = get_smart_folder_presets(lang)
    # All selected by default
    all_emojis = {r.emoji for r in presets}

    await state.set_state(AppSG.selecting_folders)
    await state.update_data(
        selected_emojis=list(all_emojis),
        folder_action="folders_only",
    )

    text = i18n.get_text("folder_selection_title", lang=lang)
    kb = get_folder_selection_kb(presets, all_emojis, lang=lang)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_folder:"))
async def cb_toggle_folder(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "ru",
) -> None:
    """Toggle a folder category on/off."""
    emoji = (callback.data or "").split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("selected_emojis", []))

    if emoji in selected:
        selected.discard(emoji)
    else:
        selected.add(emoji)

    await state.update_data(selected_emojis=list(selected))

    presets = get_smart_folder_presets(lang)
    text = i18n.get_text("folder_selection_title", lang=lang)
    kb = get_folder_selection_kb(presets, selected, lang=lang)

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data == "select_all_folders")
async def cb_select_all_folders(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "ru",
) -> None:
    """Select all folder categories."""
    presets = get_smart_folder_presets(lang)
    all_emojis = {r.emoji for r in presets}
    await state.update_data(selected_emojis=list(all_emojis))

    text = i18n.get_text("folder_selection_title", lang=lang)
    kb = get_folder_selection_kb(presets, all_emojis, lang=lang)

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data == "deselect_all_folders")
async def cb_deselect_all_folders(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "ru",
) -> None:
    """Deselect all folder categories."""
    await state.update_data(selected_emojis=[])
    presets = get_smart_folder_presets(lang)

    text = i18n.get_text("folder_selection_title", lang=lang)
    kb = get_folder_selection_kb(presets, set(), lang=lang)

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data == "back_to_diagnostic")
async def cb_back_to_diagnostic(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
) -> None:
    """Return to diagnostic results from folder selection."""
    data = await state.get_data()
    session_id = data.get("session_id")
    r = _get_redis(redis)

    if session_id:
        scan_result = await ScannerService.get_cached_scan(r, session_id)
        if scan_result:
            await state.set_state(AppSG.ready_to_clean)
            if callback.message:
                await callback.message.edit_text(
                    i18n.get_text("scan_report", lang=lang,
                                  total_dialogs=scan_result.total_dialogs,
                                  total_unread=f"{scan_result.total_unread:,}",
                                  dead_total=scan_result.dead_count + scan_result.zombie_count,
                                  dead_percentage=scan_result.dead_percentage,
                                  archived_count=scan_result.archived_count,
                                  top_list="..."),
                    reply_markup=get_diagnostic_kb(scan_result.total_unread, lang=lang),
                    parse_mode="Markdown",
                )
    await callback.answer()


@router.callback_query(F.data == "confirm_folders")
async def cb_confirm_folders(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
) -> None:
    """Execute cleanup with selected folder categories."""
    data = await state.get_data()
    session_id = data.get("session_id")
    selected_emojis = data.get("selected_emojis", [])
    folder_action = data.get("folder_action", "folders_only")

    mark_read = folder_action != "folders_only"

    if not session_id:
        if callback.message:
            await callback.message.answer(i18n.get_text("session_not_found", lang=lang))
        await callback.answer()
        return

    r = _get_redis(redis)

    await _execute_cleanup(
        callback=callback,
        state=state,
        redis=r,
        lang=lang,
        session_id=session_id,
        mark_read=mark_read,
        create_folders=True,
        selected_folders=list(selected_emojis),
    )


# --- F. Cleanup / Zen Button Flow ---


@router.callback_query(F.data.in_({"run_clean:all", "run_clean:read_only"}))
async def cb_run_clean(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
) -> None:
    """Execute cleanup actions based on user selection."""
    action = callback.data or ""
    mark_read = "folders_only" not in action
    create_folders = "read_only" not in action

    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        if callback.message:
            await callback.message.answer(i18n.get_text("session_not_found", lang=lang))
        await callback.answer()
        return

    r = _get_redis(redis)

    if create_folders:
        # Redirect to folder selection UI
        scan_result = await ScannerService.get_cached_scan(r, session_id)
        if not scan_result:
            if callback.message:
                await callback.message.answer(i18n.get_text("session_not_found", lang=lang))
            await callback.answer()
            return

        presets = get_smart_folder_presets(lang)
        all_emojis = {rule.emoji for rule in presets}
        await state.set_state(AppSG.selecting_folders)
        await state.update_data(
            selected_emojis=list(all_emojis),
            folder_action="all",
        )

        text = i18n.get_text("folder_selection_title", lang=lang)
        kb = get_folder_selection_kb(presets, all_emojis, lang=lang)

        if callback.message:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        await callback.answer()
        return

    # read_only — execute immediately without folder selection
    await _execute_cleanup(
        callback=callback,
        state=state,
        redis=r,
        lang=lang,
        session_id=session_id,
        mark_read=mark_read,
        create_folders=False,
        selected_folders=[],
    )


async def _execute_cleanup(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis,
    lang: str,
    session_id: str,
    mark_read: bool,
    create_folders: bool,
    selected_folders: list[str],
) -> None:
    """Shared cleanup execution logic."""
    user_id = callback.from_user.id if callback.from_user else 0

    async with RedisLock(redis, f"clean:{user_id}", timeout=600) as acquired:
        if not acquired:
            await callback.answer(
                i18n.get_text("action_already_running", lang=lang),
                show_alert=True,
            )
            return

        scan_result = await ScannerService.get_cached_scan(redis, session_id)
        if not scan_result:
            if callback.message:
                await callback.message.answer(i18n.get_text("session_not_found", lang=lang))
            await callback.answer()
            return

        await state.set_state(AppSG.cleaning)
        status_msg = (
            await callback.message.answer(i18n.get_text("clean_starting", lang=lang))
            if callback.message
            else None
        )
        await callback.answer()

        session_store = SessionStore(redis)
        client = await session_store.load(session_id)
        if not client:
            if status_msg:
                await status_msg.edit_text(i18n.get_text("session_not_found", lang=lang))
            return

        editor = ThrottledMessageEditor(status_msg) if status_msg else None

        async def on_clean_progress(progress) -> None:
            if editor:
                await editor.edit_text_safe(
                    i18n.get_text(
                        "clean_progress",
                        lang=lang,
                        message=progress.message,
                        current=progress.current,
                        total=progress.total,
                    )
                )

        cleaner = CleanerService()
        config = CleanConfig(
            mark_read=mark_read,
            create_folders=create_folders,
            auto_logout=False,
            selected_folders=selected_folders,
        )

        try:
            clean_result = await cleaner.execute_zen_clean(
                client=client,
                scan_result=scan_result,
                config=config,
                session_store=session_store,
                progress_callback=on_clean_progress,
                lang=lang,
            )

            # Generate Wrapped Stats & Card
            uname = callback.from_user.username if callback.from_user else None
            stats = WrappedService.calculate_wrapped_stats(
                scan_result, clean_result=clean_result, username=uname, lang=lang
            )
            await WrappedService.save_wrapped(redis, stats)

            card_png = WrappedService().generate_wrapped_card(stats, lang=lang)
            file = BufferedInputFile(card_png, filename="tazala_wrapped.png")

            caption = i18n.get_text(
                "wrapped_caption",
                lang=lang,
                archetype=stats.archetype_title,
                messages=f"{stats.messages_cleared:,}",
                hours=stats.time_saved_hours,
                score=stats.zen_score,
            )

            if callback.message:
                await callback.message.answer_photo(
                    photo=file,
                    caption=caption,
                    reply_markup=get_wrapped_kb(session_id, lang=lang),
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
                await status_msg.edit_text(f"❌ {e}")
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass


# --- G. Logout Handler ---


@router.callback_query(F.data == "session_logout")
async def cb_session_logout(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis | None = None,
    lang: str = "ru",
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

    text = i18n.get_text("logout_confirmed", lang=lang)
    welcome = i18n.get_text("start_welcome", lang=lang)
    if callback.message:
        await callback.message.answer(
            f"{text}\n\n{welcome}",
            reply_markup=get_start_kb(lang=lang),
            parse_mode="Markdown",
        )
    await callback.answer()
