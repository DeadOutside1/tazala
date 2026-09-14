"""
Schemas and data models for Telegram account scanning and dialog classification.
"""
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ChatType(StrEnum):
    """Classification of Telegram chat entity type."""

    USER = "user"
    GROUP = "group"
    CHANNEL = "channel"
    BOT = "bot"


class ChatStatus(StrEnum):
    """Activity classification status of a dialog."""

    ACTIVE = "active"        # Message <= 30 days
    MODERATE = "moderate"    # Message 31-180 days
    DEAD = "dead"            # Message > 180 days
    ZOMBIE = "zombie"        # Channel/Group inactive > 365 days or no messages


class DialogInfo(BaseModel):
    """Detailed information about an individual scanned dialog."""

    id: int
    title: str
    type: ChatType
    unread_count: int = 0
    last_message_date: datetime | None = None
    is_archived: bool = False
    is_pinned: bool = False
    folder_id: int | None = None
    status: ChatStatus


class TopUnreadChat(BaseModel):
    """Summary of a chat with unread messages for top ranking."""

    id: int
    title: str
    unread_count: int
    type: ChatType


class ScanResult(BaseModel):
    """Aggregated scan and diagnostic result of a Telegram account."""

    session_id: str
    scanned_at: datetime
    total_dialogs: int = 0
    total_unread: int = 0
    dead_count: int = 0
    zombie_count: int = 0
    active_count: int = 0
    moderate_count: int = 0
    channels_count: int = 0
    groups_count: int = 0
    users_count: int = 0
    bots_count: int = 0
    archived_count: int = 0
    dead_percentage: float = 0.0
    top_unread_chats: list[TopUnreadChat] = Field(default_factory=list)
    scan_duration_seconds: float = 0.0
    dialogs: list[DialogInfo] = Field(default_factory=list)


class ScanRequest(BaseModel):
    """Request payload to initiate account scanning."""

    session_id: str
