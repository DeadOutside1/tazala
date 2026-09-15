"""
FastAPI application factory with lifespan (Redis init/shutdown).
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.bot.bot import create_bot_and_dispatcher
from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect Redis and start Telegram Bot. Shutdown: stop Bot and close Redis."""
    logger.info("Starting up — connecting to Redis...")
    app.state.redis = Redis.from_url(settings.REDIS_URL, decode_responses=False, protocol=2)
    await app.state.redis.ping()
    logger.info("Redis connected ✅")

    bot, dp = create_bot_and_dispatcher(redis=app.state.redis)
    polling_task = None
    if bot and dp:
        polling_task = asyncio.create_task(dp.start_polling(bot))
        logger.info("Telegram Bot polling started ✅")

    yield

    if polling_task and dp and bot:
        logger.info("Stopping Telegram Bot polling...")
        await dp.stop_polling()
        await bot.session.close()
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        logger.info("Telegram Bot stopped.")

    await app.state.redis.close()
    logger.info("Redis disconnected, shutting down.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Tazala API",
        description="Telegram Info-Detox Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "tazala"}

    from app.auth.router import router as auth_router
    from app.cleaner.router import router as cleaner_router
    from app.scanner.router import router as scanner_router
    from app.wrapped.router import router as wrapped_router

    app.include_router(auth_router)
    app.include_router(scanner_router)
    app.include_router(cleaner_router)
    app.include_router(wrapped_router)

    return app


app = create_app()
