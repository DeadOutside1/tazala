"""
TelegramClient factory.
Creates ephemeral clients with empty StringSession (nothing on disk).
"""
from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config import settings


class ClientManager:
    """Factory for creating Telethon MTProto clients."""

    @staticmethod
    def create_ephemeral_client() -> TelegramClient:
        """
        Create a new TelegramClient with an empty StringSession.
        The client is NOT connected — call `await client.connect()` after creation.
        """
        client = TelegramClient(
            StringSession(""),
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
            device_model="Tazala Detox",
            system_version="1.0",
            app_version="1.0.0",
        )
        client.flood_sleep_threshold = 60
        return client

    @staticmethod
    def client_from_session_string(session_string: str) -> TelegramClient:
        """
        Create a TelegramClient from an existing StringSession.
        The client is NOT connected — call `await client.connect()` after creation.
        """
        client = TelegramClient(
            StringSession(session_string),
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
            device_model="Tazala Detox",
            system_version="1.0",
            app_version="1.0.0",
        )
        client.flood_sleep_threshold = 60
        return client
