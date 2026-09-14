"""
FastAPI router for Zen Cleanup operations (mark read and smart folders).
"""
import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.cleaner.schemas import CleanRequest, CleanResult
from app.cleaner.service import CleanerService
from app.scanner.service import ScannerService
from app.telegram.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["cleaner"])


@router.post("/clean", response_model=CleanResult)
async def clean_account(request: Request, clean_req: CleanRequest) -> CleanResult:
    """
    Execute batch cleanup: mark dialogs as read and create smart folders.
    Requires a preceding scan for the session stored in Redis.
    """
    redis = getattr(request.app.state, "redis", None)
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis service unavailable",
        )

    # 1. Verify scan result exists
    scan_result = await ScannerService.get_cached_scan(redis, clean_req.session_id)
    if not scan_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scan must be performed before cleaning. Run /api/scan first.",
        )

    # 2. Verify and load Telegram client
    session_store = SessionStore(redis)
    client = await session_store.load(clean_req.session_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found, expired, or unauthorized",
        )

    cleaner_service = CleanerService()
    destroyed = False
    try:
        result = await cleaner_service.execute_zen_clean(
            client=client,
            scan_result=scan_result,
            config=clean_req.config,
            session_store=session_store,
        )
        destroyed = result.session_destroyed
        return result
    finally:
        if not destroyed:
            try:
                await client.disconnect()
            except Exception:
                pass
