"""
WebSocket router for MTProto QR authentication.
Provides real-time interactive QR login flow with 2FA support.
"""
import base64
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.schemas import AuthState
from app.auth.service import QRAuthService
from app.telegram.client_manager import ClientManager
from app.telegram.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/qr-auth")
async def qr_auth_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint managing the full QR authentication cycle."""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info("New QR auth WebSocket connection: %s", session_id[:8])

    redis = getattr(websocket.app.state, "redis", None)
    session_store = SessionStore(redis) if redis else None
    auth_service = QRAuthService(session_store=session_store)

    client = None
    authenticated = False

    try:
        client = ClientManager.create_ephemeral_client()
        await client.connect()

        async def on_qr(url: str, png_bytes: bytes) -> None:
            await websocket.send_json({
                "type": "qr",
                "session_id": session_id,
                "url": url,
                "qr_png_base64": base64.b64encode(png_bytes).decode("utf-8"),
            })

        async def on_state(state: AuthState) -> None:
            await websocket.send_json({
                "type": "state",
                "session_id": session_id,
                "state": state.value,
            })

        result = await auth_service.start_qr_login(
            client=client,
            on_qr=on_qr,
            on_state=on_state,
            session_id=session_id,
            timeout=120,
        )

        # Handle 2FA prompt
        if result.state == AuthState.TWO_FA_REQUIRED:
            await websocket.send_json({
                "type": "2fa_required",
                "session_id": session_id,
            })

            data = await websocket.receive_json()
            if data.get("type") == "2fa_password" and "password" in data:
                result = await auth_service.complete_2fa(
                    client=client,
                    password=data["password"],
                    session_id=session_id,
                )

        if result.state == AuthState.AUTHENTICATED:
            authenticated = True
            await websocket.send_json({
                "type": "authenticated",
                "session_id": session_id,
                "user_id": result.user_id,
                "username": result.username,
            })
        else:
            await websocket.send_json({
                "type": "error",
                "session_id": session_id,
                "error": result.error or f"Authentication ended with state {result.state.value}",
            })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id[:8])
    except Exception as e:
        logger.exception("Unexpected error in QR auth WebSocket %s: %s", session_id[:8], e)
        try:
            await websocket.send_json({
                "type": "error",
                "session_id": session_id,
                "error": str(e),
            })
        except Exception:
            pass
    finally:
        # If authentication was not completed, clean up and destroy client/session
        if client:
            if not authenticated:
                if session_store:
                    await session_store.destroy(session_id, client)
                else:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
            else:
                # Keep session in Redis, disconnect socket client connection
                try:
                    await client.disconnect()
                except Exception:
                    pass
