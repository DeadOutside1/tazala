"""
Distributed concurrency lock using Redis with TTL expiry.
"""
import logging
from types import TracebackType

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisLock:
    """
    Asynchronous distributed lock using Redis atomic SETNX with expiration.
    Prevents concurrent execution of heavy operations (scan, clean) for the same user.
    """

    def __init__(self, redis: Redis, key: str, timeout: int = 120) -> None:
        self.redis = redis
        self.lock_key = f"lock:{key}"
        self.timeout = timeout
        self.acquired = False

    async def __aenter__(self) -> bool:
        """
        Attempt to acquire the lock atomically.
        Returns True if acquired, False otherwise.
        """
        try:
            res = await self.redis.set(self.lock_key, "1", ex=self.timeout, nx=True)
            self.acquired = bool(res)
        except Exception as e:
            logger.error("Failed to acquire Redis lock '%s': %s", self.lock_key, e)
            self.acquired = False
        return self.acquired

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Release the lock if it was acquired by this instance."""
        if self.acquired:
            try:
                await self.redis.delete(self.lock_key)
            except Exception as e:
                logger.error("Failed to release Redis lock '%s': %s", self.lock_key, e)
