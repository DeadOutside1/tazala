"""
CLI script for running diagnostic scans on authenticated sessions.
Run with: python -m scripts.cli_scan [<session_id>]
"""
import argparse
import asyncio
import logging
import sys

from redis.asyncio import Redis

from app.config import settings
from app.scanner.service import ScannerService
from app.telegram.session_store import SessionStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def get_target_session_id(redis: Redis, provided_id: str | None) -> str | None:
    """Resolve session_id from argument or find latest active session in Redis."""
    if provided_id:
        return provided_id

    # Scan for any session keys in Redis
    keys = await redis.keys("session:*")
    if not keys:
        return None

    # Pick the first available active session
    latest_key = keys[0]
    key_str = latest_key.decode() if isinstance(latest_key, bytes) else str(latest_key)
    return key_str.replace("session:", "")


def print_diagnostic_table(scan_result) -> None:
    """Render formatted diagnostic summary in terminal."""
    dead_total = scan_result.dead_count + scan_result.zombie_count

    print("\n" + "=" * 65)
    print("           📊 TAZALA ACCOUNT DIAGNOSTIC SUMMARY")
    print("=" * 65)
    print(f"Session ID:             {scan_result.session_id}")
    print(f"Total Dialogs:          {scan_result.total_dialogs}")
    print(f"Total Unread Messages:  {scan_result.total_unread:,}")
    print(f"Active Dialogs (<=30d): {scan_result.active_count}")
    print(f"Dead / Zombies (>180d): {dead_total} ({scan_result.dead_percentage}%)")
    print(f"Archived Dialogs:       {scan_result.archived_count}")
    print("-" * 65)
    print("🏆 TOP UNREAD CLUTTER SOURCES:")
    print("-" * 65)
    print(f"{'#':<3} | {'Chat Title':<30} | {'Unreads':<10} | {'Type':<10}")
    print("-" * 65)

    if not scan_result.top_unread_chats:
        print("No unread chats found! 🎉")
    else:
        for idx, chat in enumerate(scan_result.top_unread_chats[:10], start=1):
            title = chat.title[:28] + ".." if len(chat.title) > 30 else chat.title
            print(
                f"{idx:<3} | {title:<30} | {chat.unread_count:<10,} | {chat.type.value:<10}"
            )

    print("=" * 65 + "\n")


async def main() -> None:
    """Execute account diagnostic scan from CLI."""
    parser = argparse.ArgumentParser(description="Tazala Account Diagnostics CLI")
    parser.add_argument("session_id", nargs="?", help="Active session UUID from Redis")
    args = parser.parse_args()

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False, protocol=2)
    session_id = await get_target_session_id(redis, args.session_id)

    if not session_id:
        print("❌ No active sessions found in Redis.")
        print("Run 'python -m scripts.cli_qr' first to authenticate.")
        await redis.aclose()
        sys.exit(1)

    print(f"🔍 Loading session '{session_id}'...")
    session_store = SessionStore(redis)
    client = await session_store.load(session_id)

    if not client:
        print(f"❌ Session '{session_id}' expired or unauthorized.")
        await redis.aclose()
        sys.exit(1)

    async def on_progress(scanned: int) -> None:
        print(f"\rScanning dialogs: {scanned} processed...", end="", flush=True)

    scanner = ScannerService()
    try:
        print("Starting account scan...")
        scan_result = await scanner.scan_account(
            client=client,
            session_id=session_id,
            progress_callback=on_progress,
        )
        print("\rScanning completed!                    ")
        await scanner.save_scan_result(redis, scan_result)
        print_diagnostic_table(scan_result)

    except Exception as e:
        logger.exception("Diagnostic scan error: %s", e)
        sys.exit(1)
    finally:
        await client.disconnect()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
