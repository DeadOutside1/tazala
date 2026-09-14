"""
Schemas and models for Wrapped analytics and Spotify-style shareable stats.
"""
from enum import StrEnum

from pydantic import BaseModel


class ZenArchetype(StrEnum):
    """Behavioral digital detox archetype."""

    DIGITAL_MONK = "digital_monk"
    INFO_COLLECTOR = "info_collector"
    CHAOS_LORD = "chaos_lord"
    DIGITAL_HOARDER = "digital_hoarder"


class WrappedStats(BaseModel):
    """Comprehensive post-cleanup analytics and detox score."""

    session_id: str
    username: str | None = None
    total_dialogs: int = 0
    messages_cleared: int = 0
    dead_chats_count: int = 0
    folders_created_count: int = 0
    time_saved_hours: float = 0.0
    zen_score: int = 100
    archetype: ZenArchetype
    archetype_title: str
    archetype_description: str
    top_unread_source: str | None = None
