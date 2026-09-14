"""
QR Authentication Service for Telegram MTProto.
Zero-Knowledge: generates QR, awaits scan, handles 2FA,
and stores ephemeral session string in Redis.
Protocol agnostic (uses async callbacks).
"""
import asyncio
import io
import logging
import uuid
from collections.abc import Awaitable, Callable

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from app.auth.schemas import AuthResult, AuthState
from app.telegram.session_store import SessionStore

logger = logging.getLogger(__name__)


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
