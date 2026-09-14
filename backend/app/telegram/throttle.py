"""
Rate limiter and FloodWait-aware executor for Telethon MTProto requests.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FloodSafeExecutor:
    """Executes asynchronous calls with exponential backoff on Telegram FloodWaitError."""

    @staticmethod
    async def execute(
        coro_fn: Callable[[], Awaitable[T]],
        max_retries: int = 3,
        default_delay: float = 0.5,
    ) -> T:
        """
        Execute an async callable safely.
        If FloodWaitError is raised, wait the requested seconds (+ 1s buffer) and retry.
        Apply default_delay sleep after successful execution to prevent flood triggering.
        """
        attempts = 0
        while True:
            try:
                result = await coro_fn()
                if default_delay > 0:
                    await asyncio.sleep(default_delay)
                return result
            except FloodWaitError as err:
                attempts += 1
                wait_time = (getattr(err, "seconds", 0) or 0) + 1
                logger.warning(
                    "FloodWait encountered: sleeping %ds (attempt %d/%d)",
                    wait_time,
                    attempts,
                    max_retries,
                )
                if attempts > max_retries:
                    logger.error("FloodWait retry limit exceeded (%d)", max_retries)
                    raise
                await asyncio.sleep(wait_time)
