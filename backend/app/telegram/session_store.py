"""
Redis-based ephemeral session storage.
Sessions live ONLY in Redis memory, NEVER on disk.
TTL = 5 minutes. After use — physical deletion + log_out().
"""
import logging

from redis.asyncio import Redis
from telethon import TelegramClient

logger = logging.getLogger(__name__)


class SessionStore:
    """Manages ephemeral Telethon sessions in Redis."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.default_ttl = 1800  # 30 minutes idle TTL

    async def save(self, session_id: str, session_string: str, ttl: int | None = None) -> None:
        """Save StringSession to Redis with TTL."""
        effective_ttl = ttl or self.default_ttl
        await self.redis.setex(
            f"session:{session_id}",
            effective_ttl,
            session_string,
        )
        logger.info("Session %s... saved (TTL %ds)", session_id[:8], effective_ttl)

    async def load(self, session_id: str) -> TelegramClient | None:
        """Load session from Redis and return a connected, authorized client."""
        raw = await self.redis.get(f"session:{session_id}")
        if not raw:
            logger.warning("Session %s... not found or expired", session_id[:8])
            return None

        session_string = raw.decode() if isinstance(raw, bytes) else raw

        try:
            from app.telegram.client_manager import ClientManager

            client = ClientManager.client_from_session_string(session_string)
            await client.connect()

            if not await client.is_user_authorized():
                logger.warning("Session %s... is no longer authorized", session_id[:8])
                await self.destroy(session_id, client)
                return None

            # Automatically extend TTL on active usage
            await self.extend_ttl(session_id, self.default_ttl)

            return client
        except Exception as e:
            logger.warning("Failed to load or initialize session %s...: %s", session_id[:8], e)
            await self.destroy(session_id)
            return None

    async def destroy(self, session_id: str, client: TelegramClient | None = None) -> None:
        """
        Zero-Knowledge destruction: Telegram log_out + Redis DEL.
        Invalidates the auth key on Telegram servers.
        """
        if client:
            try:
                await client.log_out()
                logger.info("Session %s... destroyed (log_out)", session_id[:8])
            except Exception as e:
                logger.warning("log_out() failed for %s...: %s", session_id[:8], e)
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass

        await self.redis.delete(f"session:{session_id}")
        logger.info("Session %s... removed from Redis", session_id[:8])

    async def extend_ttl(self, session_id: str, extra_seconds: int = 120) -> None:
        """Extend session TTL (e.g. during long cleanup operations)."""
        await self.redis.expire(f"session:{session_id}", extra_seconds)
        logger.info("Session %s... TTL extended by %ds", session_id[:8], extra_seconds)

    async def exists(self, session_id: str) -> bool:
        """Check if an active session exists in Redis."""
        return bool(await self.redis.exists(f"session:{session_id}"))

