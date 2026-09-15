"""
CLI script for interactive Telegram QR authentication debugging.
Run with: python -m scripts.cli_qr
"""
import asyncio
import getpass
import logging
import sys

import qrcode
from redis.asyncio import Redis

from app.auth.schemas import AuthState
from app.auth.service import QRAuthService
from app.config import settings
from app.telegram.client_manager import ClientManager
from app.telegram.session_store import SessionStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Execute QR login from command line."""
    print("=" * 60)
    print("🚀 Tazala MTProto QR-Login Debugger")
    print("=" * 60)

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False, protocol=2)
    session_store = SessionStore(redis)
    auth_service = QRAuthService(session_store=session_store)

    client = ClientManager.create_ephemeral_client()
    await client.connect()

    async def on_qr(url: str, _png_bytes: bytes) -> None:
        print("\n" + "-" * 50)
        print("📲 Scan this QR code in Telegram (Settings ➔ Devices ➔ Link):")
        print("-" * 50 + "\n")
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.print_ascii(invert=True)
        print(f"\n🔗 Direct Telegram link: {url}\n")
        print("Waiting for scan (auto-refreshes every 25s)...")

    async def on_state(state: AuthState) -> None:
        logger.info("Current AuthState: %s", state.value)

    try:
        result = await auth_service.start_qr_login(
            client=client,
            on_qr=on_qr,
            on_state=on_state,
            timeout=120,
        )

        if result.state == AuthState.TWO_FA_REQUIRED:
            print("\n🔒 Two-Factor Authentication (2FA) is enabled on this account.")
            password = getpass.getpass("Enter 2FA cloud password: ")
            result = await auth_service.complete_2fa(
                client=client,
                password=password,
                session_id=result.session_id,
            )

        if result.state == AuthState.AUTHENTICATED:
            print("\n" + "=" * 60)
            print("✅ AUTHENTICATION SUCCESSFUL!")
            print(f"Session ID:     {result.session_id}")
            print(f"Session String: {result.session_string}")
            print("=" * 60)
            print("Session saved in Redis with 5-minute TTL.")
        else:
            print(f"\n❌ Authentication finished with status: {result.state.value}")
            sys.exit(1)

    except Exception as e:
        logger.exception("Login failed: %s", e)
        sys.exit(1)
    finally:
        await client.disconnect()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
