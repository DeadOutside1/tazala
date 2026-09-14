"""
FastAPI router for account diagnostic scanning.
"""
import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.scanner.schemas import ScanRequest, ScanResult
from app.scanner.service import ScannerService
from app.telegram.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scanner"])


@router.post("/scan", response_model=ScanResult)
async def scan_account(request: Request, scan_req: ScanRequest) -> ScanResult:
    """
    Trigger diagnostics and dialog scanning for an authenticated Telegram session.
    Results are cached in Redis for fast retrieval by subsequent cleaner/wrapped steps.
    """
    redis = getattr(request.app.state, "redis", None)
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis service unavailable",
        )

    session_store = SessionStore(redis)
    client = await session_store.load(scan_req.session_id)

    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found, expired, or unauthorized",
        )

    scanner_service = ScannerService()
    try:
        result = await scanner_service.scan_account(client, scan_req.session_id)
        await scanner_service.save_scan_result(redis, result)
        return result
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


@router.get("/scan/{session_id}", response_model=ScanResult)
async def get_scan_result(request: Request, session_id: str) -> ScanResult:
    """Retrieve previously cached scan result from Redis."""
    redis = getattr(request.app.state, "redis", None)
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis service unavailable",
        )

    cached = await ScannerService.get_cached_scan(redis, session_id)
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan result not found or expired",
        )

    return cached
