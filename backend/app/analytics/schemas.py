"""
Pydantic schemas for Tazala Analytics, Ratings & Feedback.
"""
from pydantic import BaseModel, Field


class ReviewItem(BaseModel):
    """User review & rating submission."""

    user_id: int
    username: str | None = None
    rating: int = Field(ge=1, le=5, description="1 to 5 star rating")
    comment: str = ""
    created_at: str = ""


class AnalyticsSummary(BaseModel):
    """Aggregated global metrics for Tazala bot usage."""

    total_users: int = 0
    total_scans: int = 0
    total_cleans: int = 0
    messages_marked: int = 0
    folders_created: int = 0
    time_saved_hours: float = 0.0
    ratings_count: int = 0
    avg_rating: float = 0.0
