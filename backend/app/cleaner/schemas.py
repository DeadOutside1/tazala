"""
Schemas and configurations for the Cleaner module (mark read & smart folders).
"""
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class CleanStep(StrEnum):
    """Execution step of the Zen Cleanup pipeline."""

    MARK_READ = "mark_read"
    CREATE_FOLDERS = "create_folders"
    LOGOUT = "logout"
    COMPLETED = "completed"


class UserFolderInfo(BaseModel):
    """Information about an existing Telegram dialog folder."""

    id: int
    title: str
    emoticon: str | None = None
    chats_count: int = 0


class FolderRule(BaseModel):
    """Definition of a smart folder categorization rule."""

    title: str
    emoji: str = ""
    categories: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title_length(cls, v: str) -> str:
        """Telegram folder names are strictly limited to 12 characters max."""
        if len(v) > 12:
            raise ValueError(f"Folder title '{v}' exceeds 12 characters limit ({len(v)} chars)")
        return v


class CleanConfig(BaseModel):
    """User configuration for the Zen Cleanup operation."""

    mark_read: bool = True
    create_folders: bool = True
    auto_logout: bool = False
    delay_per_dialog: float = 0.5
    selected_folders: list[str] = Field(default_factory=list)


class CleanProgress(BaseModel):
    """Real-time progress notification during cleanup."""

    session_id: str
    step: CleanStep
    current: int
    total: int
    message: str


class CleanResult(BaseModel):
    """Outcome and summary of the Zen Cleanup execution."""

    session_id: str
    messages_marked: int
    folders_created: list[str]
    duration_seconds: float
    session_destroyed: bool


class CleanRequest(BaseModel):
    """Payload to trigger Zen Cleanup."""

    session_id: str
    config: CleanConfig = Field(default_factory=CleanConfig)
