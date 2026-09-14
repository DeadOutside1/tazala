"""
FastAPI router for Wrapped detox analytics and visual card generation.
"""
import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.scanner.service import ScannerService
from app.wrapped.schemas import WrappedStats
from app.wrapped.service import WrappedService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wrapped", tags=["wrapped"])


async def _get_or_compute_wrapped(request: Request, session_id: str) -> WrappedStats:
    """Helper to fetch cached WrappedStats or compute them from cached scan result."""
    redis = getattr(request.app.state, "redis", None)
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis service unavailable",
        )

    # 1. Check wrapped cache
    stats = await WrappedService.get_cached_wrapped(redis, session_id)
    if stats:
        return stats

    # 2. Compute from scan result if available
    scan_result = await ScannerService.get_cached_scan(redis, session_id)
    if not scan_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scan or cleanup records found for this session",
        )

    wrapped_service = WrappedService()
    stats = wrapped_service.calculate_wrapped_stats(scan_result)
    await wrapped_service.save_wrapped(redis, stats)
    return stats


@router.get("/{session_id}", response_model=WrappedStats)
async def get_wrapped_stats(request: Request, session_id: str) -> WrappedStats:
    """Get JSON summary of user's detox analytics, archetype, and Zen Score."""
    return await _get_or_compute_wrapped(request, session_id)


@router.get("/{session_id}/card.png")
async def get_wrapped_card(request: Request, session_id: str) -> Response:
    """Generate and return 1080x1350 PNG image card ready for sharing."""
    stats = await _get_or_compute_wrapped(request, session_id)
    wrapped_service = WrappedService()
    png_bytes = wrapped_service.generate_wrapped_card(stats)
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
