"""
Application settings loaded from environment variables.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Core application settings."""

    # Telegram API (from https://my.telegram.org)
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""

    # Telegram Bot (from @BotFather)
    TELEGRAM_BOT_TOKEN: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    # Admin Telegram user IDs (comma-separated, e.g. "8041783822")
    ADMIN_USER_IDS: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def admin_ids(self) -> set[int]:
        """Return parsed set of integer Telegram user IDs authorized as admins."""
        if not self.ADMIN_USER_IDS:
            return set()
        return {
            int(x.strip())
            for x in self.ADMIN_USER_IDS.split(",")
            if x.strip().isdigit()
        }



settings = Settings()
