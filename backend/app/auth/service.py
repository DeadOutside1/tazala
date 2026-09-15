"""
Authentication Services for Telegram MTProto.
QR Login: generates QR, awaits scan, handles 2FA, stores ephemeral session.
Phone Login: sends code via Telegram 777000, handles SMS code + 2FA.
Zero-Knowledge: sessions stored ONLY in Redis RAM with 5-minute TTL.
"""
import asyncio
import io
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl import types

from app.auth.schemas import AuthResult, AuthState
from app.telegram.session_store import SessionStore

logger = logging.getLogger(__name__)


@dataclass
class SendCodeResult:
    """Result of MTProto send_code / resend_code request."""

    phone_code_hash: str
    delivery_type: str = "app"  # "app" | "sms" | "email" | "call" | "fragment"
    timeout: int | None = None
    email_pattern: str | None = None

    def __str__(self) -> str:
        return self.phone_code_hash

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.phone_code_hash == other
        return super().__eq__(other)


class QRAuthService:
    """Handles MTProto QR code authentication lifecycle."""

    def __init__(self, session_store: SessionStore | None = None) -> None:
        self.session_store = session_store

    @staticmethod
    def generate_qr_png(url: str) -> bytes:
        """Generate PNG image bytes from a QR URL."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    async def start_qr_login(
        self,
        client: TelegramClient,
        on_qr: Callable[[str, bytes], Awaitable[None]],
        on_state: Callable[[AuthState], Awaitable[None]],
        session_id: str | None = None,
        timeout: int = 120,
    ) -> AuthResult:
        """
        Start QR login flow, periodically refreshing token until scan or timeout.
        
        Args:
            client: Connected TelegramClient instance.
            on_qr: Callback for new QR url and PNG bytes.
            on_state: Callback for AuthState transitions.
            session_id: Unique session identifier (generates uuid4 if not provided).
            timeout: Total timeout in seconds (default 120).
        """
        sid = session_id or str(uuid.uuid4())

        try:
            qr = await client.qr_login()
            png_bytes = self.generate_qr_png(qr.url)
            await on_qr(qr.url, png_bytes)
            await on_state(AuthState.QR_GENERATED)

            # Each QR token typically lasts ~30 seconds; wait 25s per attempt
            interval = 25
            max_attempts = max(1, timeout // interval)

            for attempt in range(max_attempts):
                try:
                    await on_state(AuthState.WAITING_SCAN)
                    await asyncio.wait_for(qr.wait(), timeout=interval)
                    break
                except TimeoutError:
                    if attempt < max_attempts - 1:
                        logger.info(
                            "QR token expired, recreating (attempt %d/%d)",
                            attempt + 1,
                            max_attempts,
                        )
                        await qr.recreate()
                        png_bytes = self.generate_qr_png(qr.url)
                        await on_qr(qr.url, png_bytes)
                        await on_state(AuthState.QR_GENERATED)
                    else:
                        logger.info("QR login timed out for session %s", sid[:8])
                        await on_state(AuthState.EXPIRED)
                        return AuthResult(
                            session_id=sid,
                            state=AuthState.EXPIRED,
                            error="QR login expired",
                        )

            # Check if user needs 2FA password
            me = await client.get_me()
            session_string = client.session.save()

            if self.session_store:
                await self.session_store.save(sid, session_string, ttl=300)

            await on_state(AuthState.AUTHENTICATED)
            return AuthResult(
                session_id=sid,
                state=AuthState.AUTHENTICATED,
                user_id=getattr(me, "id", None),
                username=getattr(me, "username", None),
            )

        except SessionPasswordNeededError:
            logger.info("2FA password required for session %s", sid[:8])
            await on_state(AuthState.TWO_FA_REQUIRED)
            return AuthResult(session_id=sid, state=AuthState.TWO_FA_REQUIRED)

        except Exception as e:
            logger.exception("Error during QR login for session %s: %s", sid[:8], e)
            await on_state(AuthState.FAILED)
            return AuthResult(session_id=sid, state=AuthState.FAILED, error=str(e))

    async def complete_2fa(
        self,
        client: TelegramClient,
        password: str,
        session_id: str,
    ) -> AuthResult:
        """Complete sign-in using 2FA password and persist StringSession in Redis."""
        try:
            await client.sign_in(password=password)
            me = await client.get_me()
            session_string = client.session.save()

            if self.session_store:
                await self.session_store.save(session_id, session_string, ttl=300)

            logger.info("2FA sign-in succeeded for session %s", session_id[:8])
            return AuthResult(
                session_id=session_id,
                state=AuthState.AUTHENTICATED,
                user_id=getattr(me, "id", None),
                username=getattr(me, "username", None),
            )
        except Exception as e:
            logger.warning("2FA sign-in failed for session %s: %s", session_id[:8], e)
            return AuthResult(
                session_id=session_id,
                state=AuthState.FAILED,
                error=str(e),
            )


class PhoneAuthService:
    """Handles MTProto phone number authentication lifecycle.

    Flow:
    1. send_code() → user receives 5-digit code from Telegram (account 777000)
    2. sign_in_with_code() → complete login with code
    3. If 2FA enabled → complete_2fa() with cloud password
    """

    def __init__(self, session_store: SessionStore | None = None) -> None:
        self.session_store = session_store

    async def send_code(
        self,
        client: TelegramClient,
        phone: str,
    ) -> SendCodeResult:
        """
        Send verification code to user's Telegram account.

        Returns:
            SendCodeResult with phone_code_hash, delivery_type, timeout, and email_pattern.
        """
        sanitized_phone = re.sub(r"[^\d+]", "", phone.strip())
        result = await client.send_code_request(sanitized_phone)
        phone_code_hash = result.phone_code_hash

        delivery_type = "app"
        email_pattern = None
        t = getattr(result, "type", None)
        if isinstance(t, types.auth.SentCodeTypeApp):
            delivery_type = "app"
        elif isinstance(t, types.auth.SentCodeTypeSms):
            delivery_type = "sms"
        elif isinstance(t, types.auth.SentCodeTypeEmailCode):
            delivery_type = "email"
        elif isinstance(
            t,
            (
                types.auth.SentCodeTypeCall,
                types.auth.SentCodeTypeFlashCall,
                types.auth.SentCodeTypeMissedCall,
            ),
        ):
            delivery_type = "call"
        elif isinstance(t, types.auth.SentCodeTypeFragmentSms):
            delivery_type = "fragment"
        elif t is not None:
            delivery_type = type(t).__name__.replace("SentCodeType", "").lower()

        timeout = getattr(result, "timeout", None)
        logger.info(
            "Verification code sent to %s...%s: delivery=%s, timeout=%s",
            sanitized_phone[:4],
            sanitized_phone[-2:],
            delivery_type,
            timeout,
        )
        return SendCodeResult(
            phone_code_hash=phone_code_hash,
            delivery_type=delivery_type,
            timeout=timeout,
            email_pattern=email_pattern,
        )

    async def resend_code(
        self,
        client: TelegramClient,
        phone: str,
        phone_code_hash: str,
    ) -> SendCodeResult:
        """Resend verification code via MTProto ResendCodeRequest."""
        from telethon.tl.functions.auth import ResendCodeRequest

        sanitized_phone = re.sub(r"[^\d+]", "", phone.strip())
        result = await client(
            ResendCodeRequest(
                phone_number=sanitized_phone,
                phone_code_hash=phone_code_hash,
            )
        )
        new_hash = getattr(result, "phone_code_hash", phone_code_hash)
        delivery_type = "app"
        email_pattern = None
        t = getattr(result, "type", None)
        if isinstance(t, types.auth.SentCodeTypeApp):
            delivery_type = "app"
        elif isinstance(t, types.auth.SentCodeTypeSms):
            delivery_type = "sms"
        elif isinstance(t, types.auth.SentCodeTypeEmailCode):
            delivery_type = "email"
            email_pattern = getattr(t, "email_pattern", None)
        elif isinstance(t, (types.auth.SentCodeTypeCall, types.auth.SentCodeTypeFlashCall)):
            delivery_type = "call"
        elif t is not None:
            delivery_type = type(t).__name__.replace("SentCodeType", "").lower()

        logger.info(
            "Resent verification code for %s...%s: delivery=%s",
            sanitized_phone[:4],
            sanitized_phone[-2:],
            delivery_type,
        )
        return SendCodeResult(
            phone_code_hash=new_hash,
            delivery_type=delivery_type,
            timeout=getattr(result, "timeout", None),
            email_pattern=email_pattern,
        )

    async def sign_in_with_code(
        self,
        client: TelegramClient,
        phone: str,
        code: str,
        phone_code_hash: str,
        session_id: str,
    ) -> AuthResult:
        """
        Complete sign-in with SMS/Telegram code.
        If 2FA is enabled, returns TWO_FA_REQUIRED state.
        """
        sanitized_phone = re.sub(r"[^\d+]", "", phone.strip())
        sanitized_code = code.strip().replace(" ", "").replace("-", "")
        try:
            await client.sign_in(
                phone=sanitized_phone,
                code=sanitized_code,
                phone_code_hash=phone_code_hash,
            )

            me = await client.get_me()
            session_string = client.session.save()

            if self.session_store:
                await self.session_store.save(session_id, session_string, ttl=300)

            logger.info("Phone sign-in succeeded for session %s", session_id[:8])
            return AuthResult(
                session_id=session_id,
                state=AuthState.AUTHENTICATED,
                user_id=getattr(me, "id", None),
                username=getattr(me, "username", None),
            )

        except SessionPasswordNeededError:
            logger.info("2FA password required after phone auth for session %s", session_id[:8])
            return AuthResult(session_id=session_id, state=AuthState.TWO_FA_REQUIRED)

        except Exception as e:
            logger.warning("Phone sign-in failed for session %s: %s", session_id[:8], e)
            return AuthResult(
                session_id=session_id,
                state=AuthState.FAILED,
                error=str(e),
            )

    async def complete_2fa(
        self,
        client: TelegramClient,
        password: str,
        session_id: str,
    ) -> AuthResult:
        """Complete sign-in using 2FA password (reuses QRAuthService logic)."""
        try:
            await client.sign_in(password=password)
            me = await client.get_me()
            session_string = client.session.save()

            if self.session_store:
                await self.session_store.save(session_id, session_string, ttl=300)

            logger.info("2FA sign-in (phone flow) succeeded for session %s", session_id[:8])
            return AuthResult(
                session_id=session_id,
                state=AuthState.AUTHENTICATED,
                user_id=getattr(me, "id", None),
                username=getattr(me, "username", None),
            )
        except Exception as e:
            logger.warning("2FA sign-in (phone flow) failed for session %s: %s", session_id[:8], e)
            return AuthResult(
                session_id=session_id,
                state=AuthState.FAILED,
                error=str(e),
            )
