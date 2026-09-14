"""
Auth module schemas — states and Pydantic models for QR login flow.
"""
from enum import StrEnum

from pydantic import BaseModel


class AuthState(StrEnum):
    """States of the QR authentication flow."""

    QR_GENERATED = "qr_generated"
    WAITING_SCAN = "waiting_scan"
    TWO_FA_REQUIRED = "2fa_required"
    AUTHENTICATED = "authenticated"
    FAILED = "failed"
    EXPIRED = "expired"


class QRAuthResponse(BaseModel):
    """Response sent to client when QR is generated."""

    session_id: str
    qr_url: str
    state: AuthState


class TwoFARequest(BaseModel):
    """Client request to complete 2FA."""

    session_id: str
    password: str


class AuthResult(BaseModel):
    """Final result of the authentication flow."""

    session_id: str
    state: AuthState
    user_id: int | None = None
    username: str | None = None
    error: str | None = None
