"""
FastAPI application factory with lifespan (Redis init/shutdown).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect Redis. Shutdown: close Redis."""
    logger.info("Starting up — connecting to Redis...")
    app.state.redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    await app.state.redis.ping()
    logger.info("Redis connected ✅")
    yield
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

    # Routers will be included here as modules are developed:
    # from app.auth.router import router as auth_router
    # app.include_router(auth_router)

    return app


app = create_app()
