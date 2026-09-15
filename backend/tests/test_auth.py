"""
Unit tests for the authentication and session management layer.
Tests SessionStore, ClientManager, and QRAuthService (including 2FA handling).
"""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image
from telethon.errors import SessionPasswordNeededError

from app.auth.schemas import AuthState
from app.auth.service import QRAuthService
from app.config import settings
from app.telegram.client_manager import ClientManager
from app.telegram.session_store import SessionStore


@pytest.fixture(autouse=True)
def setup_test_settings():
    """Ensure test environment has valid dummy Telegram API credentials."""
    original_id = settings.TELEGRAM_API_ID
    original_hash = settings.TELEGRAM_API_HASH

    settings.TELEGRAM_API_ID = 123456
    settings.TELEGRAM_API_HASH = "0123456789abcdef0123456789abcdef"

    yield

    settings.TELEGRAM_API_ID = original_id
    settings.TELEGRAM_API_HASH = original_hash


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock()
    redis.delete = AsyncMock()
    redis.expire = AsyncMock()
    return redis


@pytest.fixture
def session_store(mock_redis: AsyncMock) -> SessionStore:
    return SessionStore(mock_redis)


# --- 1. SessionStore Tests ---


@pytest.mark.asyncio
async def test_session_store_save(session_store: SessionStore, mock_redis: AsyncMock):
    """Test saving session to Redis with default and custom TTL."""
    await session_store.save("sess-1", "session_string_data")
    mock_redis.setex.assert_awaited_once_with("session:sess-1", 300, "session_string_data")

    mock_redis.setex.reset_mock()
    await session_store.save("sess-2", "custom_ttl_data", ttl=600)
    mock_redis.setex.assert_awaited_once_with("session:sess-2", 600, "custom_ttl_data")


@pytest.mark.asyncio
async def test_session_store_load_success(session_store: SessionStore, mock_redis: AsyncMock):
    """Test loading valid authorized session from Redis."""
    mock_redis.get.return_value = b"test_session_string"

    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.is_user_authorized = AsyncMock(return_value=True)

    with patch("app.telegram.session_store.StringSession"), \
         patch("app.telegram.session_store.TelegramClient", return_value=mock_client):
        client = await session_store.load("sess-1")

    assert client is mock_client
    mock_client.connect.assert_awaited_once()
    mock_client.is_user_authorized.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_store_load_expired_or_not_found(
    session_store: SessionStore, mock_redis: AsyncMock
):
    """Test loading non-existent or expired session returns None."""
    mock_redis.get.return_value = None
    client = await session_store.load("non_existent")
    assert client is None


@pytest.mark.asyncio
async def test_session_store_load_unauthorized_destroys_session(
    session_store: SessionStore, mock_redis: AsyncMock
):
    """Test loading unauthorized session triggers destroy and returns None."""
    mock_redis.get.return_value = b"unauthorized_session"

    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.is_user_authorized = AsyncMock(return_value=False)
    mock_client.log_out = AsyncMock()
    mock_client.disconnect = AsyncMock()

    with patch("app.telegram.session_store.StringSession"), \
         patch("app.telegram.session_store.TelegramClient", return_value=mock_client):
        client = await session_store.load("invalid-sess")

    assert client is None
    mock_client.log_out.assert_awaited_once()
    mock_client.disconnect.assert_awaited_once()
    mock_redis.delete.assert_awaited_once_with("session:invalid-sess")


@pytest.mark.asyncio
async def test_session_store_load_malformed_string(
    session_store: SessionStore, mock_redis: AsyncMock
):
    """Test loading corrupted/malformed session string destroys key and returns None."""
    mock_redis.get.return_value = b"corrupted_session"

    with patch("app.telegram.session_store.StringSession", side_effect=ValueError("Bad session")):
        client = await session_store.load("corrupted-sess")

    assert client is None
    mock_redis.delete.assert_awaited_once_with("session:corrupted-sess")


@pytest.mark.asyncio
async def test_session_store_destroy_with_client(
    session_store: SessionStore, mock_redis: AsyncMock
):
    """Test Zero-Knowledge destruction: log_out + disconnect + redis delete."""
    mock_client = AsyncMock()
    mock_client.log_out = AsyncMock()
    mock_client.disconnect = AsyncMock()

    await session_store.destroy("sess-1", client=mock_client)

    mock_client.log_out.assert_awaited_once()
    mock_client.disconnect.assert_awaited_once()
    mock_redis.delete.assert_awaited_once_with("session:sess-1")


@pytest.mark.asyncio
async def test_session_store_destroy_handles_logout_network_error(
    session_store: SessionStore, mock_redis: AsyncMock
):
    """Test destroy still deletes from Redis even if client.log_out() raises an error."""
    mock_client = AsyncMock()
    mock_client.log_out = AsyncMock(side_effect=ConnectionError("Network disconnected"))
    mock_client.disconnect = AsyncMock()

    await session_store.destroy("sess-err", client=mock_client)

    mock_client.disconnect.assert_awaited_once()
    mock_redis.delete.assert_awaited_once_with("session:sess-err")


@pytest.mark.asyncio
async def test_session_store_extend_ttl(session_store: SessionStore, mock_redis: AsyncMock):
    """Test extending session TTL."""
    await session_store.extend_ttl("sess-1", extra_seconds=180)
    mock_redis.expire.assert_awaited_once_with("session:sess-1", 180)


# --- 2. ClientManager Tests ---


def test_client_manager_create_ephemeral():
    """Test ephemeral client creation settings."""
    client = ClientManager.create_ephemeral_client()
    assert client.flood_sleep_threshold == 60
    assert client.session.save() == ""  # empty StringSession


def test_client_manager_from_session_string():
    """Test client initialization from session string."""
    with patch("app.telegram.client_manager.StringSession") as mock_ss:
        from telethon.sessions import StringSession as RealStringSession

        mock_ss.return_value = RealStringSession("")
        client = ClientManager.client_from_session_string("1B3dummy_session")
        assert client.flood_sleep_threshold == 60
        mock_ss.assert_called_once_with("1B3dummy_session")


# --- 3. QR Generation Tests ---


def test_generate_qr_png_valid_image():
    """Test QR code PNG generation returns valid PNG bytes."""
    test_url = "tg://login?token=AQAA_test_token_12345"
    png_bytes = QRAuthService.generate_qr_png(test_url)

    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 0
    # PNG Magic bytes signature
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    # Verify PIL can open it as a valid PNG
    image = Image.open(io.BytesIO(png_bytes))
    assert image.format == "PNG"
    assert image.size[0] > 0
    assert image.size[1] > 0


# --- 4. QRAuthService Tests (including 2FA) ---


@pytest.mark.asyncio
async def test_qr_login_success(session_store: SessionStore):
    """Test successful QR login flow without 2FA."""
    service = QRAuthService(session_store=session_store)

    mock_qr = AsyncMock()
    mock_qr.url = "tg://login?token=fake_token"
    mock_qr.wait = AsyncMock(return_value=True)

    mock_client = AsyncMock()
    mock_client.qr_login = AsyncMock(return_value=mock_qr)
    mock_me = MagicMock()
    mock_me.id = 99887766
    mock_me.username = "zen_master"
    mock_client.get_me = AsyncMock(return_value=mock_me)
    mock_client.session.save = MagicMock(return_value="saved_session_str")

    qr_calls = []
    state_calls = []

    async def on_qr(url: str, png_bytes: bytes) -> None:
        qr_calls.append((url, png_bytes))

    async def on_state(state: AuthState) -> None:
        state_calls.append(state)

    result = await service.start_qr_login(
        client=mock_client,
        on_qr=on_qr,
        on_state=on_state,
        session_id="test-session-123",
        timeout=120,
    )

    assert result.state == AuthState.AUTHENTICATED
    assert result.user_id == 99887766
    assert result.username == "zen_master"
    assert len(qr_calls) == 1
    assert qr_calls[0][0] == "tg://login?token=fake_token"
    assert AuthState.AUTHENTICATED in state_calls

    # Check session was saved in SessionStore
    session_store.redis.setex.assert_awaited_once_with(
        "session:test-session-123", 300, "saved_session_str"
    )


@pytest.mark.asyncio
async def test_qr_login_2fa_required(session_store: SessionStore):
    """Test handling of SessionPasswordNeededError (2FA prompt)."""
    service = QRAuthService(session_store=session_store)

    mock_qr = AsyncMock()
    mock_qr.url = "tg://login?token=2fa_token"
    # Telethon raises SessionPasswordNeededError when QR scan succeeds but 2FA is on
    mock_qr.wait = AsyncMock(side_effect=SessionPasswordNeededError(request=None))

    mock_client = AsyncMock()
    mock_client.qr_login = AsyncMock(return_value=mock_qr)

    state_calls = []

    async def on_qr(url: str, png: bytes) -> None:
        pass

    async def on_state(state: AuthState) -> None:
        state_calls.append(state)

    result = await service.start_qr_login(
        client=mock_client,
        on_qr=on_qr,
        on_state=on_state,
        session_id="session-2fa",
    )

    assert result.state == AuthState.TWO_FA_REQUIRED
    assert AuthState.TWO_FA_REQUIRED in state_calls
    # Session shouldn't be saved yet
    session_store.redis.setex.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_2fa_success(session_store: SessionStore):
    """Test completing 2FA with password successfully persists session."""
    service = QRAuthService(session_store=session_store)

    mock_client = AsyncMock()
    mock_client.sign_in = AsyncMock()
    mock_me = MagicMock()
    mock_me.id = 112233
    mock_me.username = "verified_user"
    mock_client.get_me = AsyncMock(return_value=mock_me)
    mock_client.session.save = MagicMock(return_value="post_2fa_session_str")

    result = await service.complete_2fa(
        client=mock_client,
        password="secret_password",
        session_id="session-2fa-complete",
    )

    assert result.state == AuthState.AUTHENTICATED
    assert result.user_id == 112233
    assert result.username == "verified_user"
    mock_client.sign_in.assert_awaited_once_with(password="secret_password")
    session_store.redis.setex.assert_awaited_once_with(
        "session:session-2fa-complete", 300, "post_2fa_session_str"
    )


@pytest.mark.asyncio
async def test_complete_2fa_wrong_password(session_store: SessionStore):
    """Test completing 2FA with invalid password returns FAILED state."""
    service = QRAuthService(session_store=session_store)

    mock_client = AsyncMock()
    mock_client.sign_in = AsyncMock(side_effect=ValueError("Invalid 2FA password"))

    result = await service.complete_2fa(
        client=mock_client,
        password="wrong_password",
        session_id="session-2fa-fail",
    )

    assert result.state == AuthState.FAILED
    assert "Invalid 2FA password" in (result.error or "")
    session_store.redis.setex.assert_not_awaited()


# --- 5. PhoneAuthService Tests ---


@pytest.mark.asyncio
async def test_phone_send_code(session_store: SessionStore):
    """Test send_code calls send_code_request and returns phone_code_hash."""
    from app.auth.service import PhoneAuthService

    service = PhoneAuthService(session_store=session_store)

    mock_client = AsyncMock()
    mock_result = MagicMock()
    mock_result.phone_code_hash = "abc123hash"
    mock_client.send_code_request = AsyncMock(return_value=mock_result)

    phone_code_hash = await service.send_code(mock_client, "+77001234567")

    assert phone_code_hash == "abc123hash"
    mock_client.send_code_request.assert_awaited_once_with("+77001234567")


@pytest.mark.asyncio
async def test_phone_sign_in_success(session_store: SessionStore):
    """Test successful phone sign-in persists session."""
    from app.auth.service import PhoneAuthService

    service = PhoneAuthService(session_store=session_store)

    mock_client = AsyncMock()
    mock_client.sign_in = AsyncMock()
    mock_me = MagicMock()
    mock_me.id = 554433
    mock_me.username = "phone_user"
    mock_client.get_me = AsyncMock(return_value=mock_me)
    mock_client.session.save = MagicMock(return_value="phone_session_str")

    result = await service.sign_in_with_code(
        client=mock_client,
        phone="+77001234567",
        code="12345",
        phone_code_hash="abc123hash",
        session_id="phone-sess-1",
    )

    assert result.state == AuthState.AUTHENTICATED
    assert result.user_id == 554433
    assert result.username == "phone_user"
    mock_client.sign_in.assert_awaited_once_with(
        phone="+77001234567", code="12345", phone_code_hash="abc123hash",
    )
    session_store.redis.setex.assert_awaited_once_with(
        "session:phone-sess-1", 300, "phone_session_str",
    )


@pytest.mark.asyncio
async def test_phone_sign_in_2fa_required(session_store: SessionStore):
    """Test phone sign-in returns TWO_FA_REQUIRED when 2FA is enabled."""
    from app.auth.service import PhoneAuthService

    service = PhoneAuthService(session_store=session_store)

    mock_client = AsyncMock()
    mock_client.sign_in = AsyncMock(
        side_effect=SessionPasswordNeededError(request=None),
    )

    result = await service.sign_in_with_code(
        client=mock_client,
        phone="+77001234567",
        code="12345",
        phone_code_hash="abc123hash",
        session_id="phone-sess-2fa",
    )

    assert result.state == AuthState.TWO_FA_REQUIRED
    session_store.redis.setex.assert_not_awaited()


@pytest.mark.asyncio
async def test_phone_sign_in_wrong_code(session_store: SessionStore):
    """Test phone sign-in with wrong code returns FAILED."""
    from app.auth.service import PhoneAuthService

    service = PhoneAuthService(session_store=session_store)

    mock_client = AsyncMock()
    mock_client.sign_in = AsyncMock(
        side_effect=ValueError("The confirmation code is invalid"),
    )

    result = await service.sign_in_with_code(
        client=mock_client,
        phone="+77001234567",
        code="99999",
        phone_code_hash="abc123hash",
        session_id="phone-sess-fail",
    )

    assert result.state == AuthState.FAILED
    assert "invalid" in (result.error or "").lower()
    session_store.redis.setex.assert_not_awaited()


@pytest.mark.asyncio
async def test_phone_and_code_sanitization(session_store: SessionStore):
    """Verify phone and verification code are properly sanitized (spaces, dashes, parens)."""
    from app.auth.service import PhoneAuthService

    service = PhoneAuthService(session_store=session_store)

    mock_client = AsyncMock()
    mock_result = MagicMock()
    mock_result.phone_code_hash = "hash_clean"
    mock_client.send_code_request = AsyncMock(return_value=mock_result)

    # 1. Test phone sanitization in send_code
    await service.send_code(mock_client, " +7 (700) 123-45-67 ")
    mock_client.send_code_request.assert_awaited_once_with("+77001234567")

    # 2. Test phone and code sanitization in sign_in_with_code
    mock_client.sign_in = AsyncMock()
    mock_me = MagicMock(id=111, username="clean_user")
    mock_client.get_me = AsyncMock(return_value=mock_me)
    mock_client.session.save = MagicMock(return_value="sess_str")

    result = await service.sign_in_with_code(
        client=mock_client,
        phone="+7 700 123 45 67",
        code=" 1 2 - 3 4 5 ",
        phone_code_hash="hash_clean",
        session_id="sess-clean",
    )

    assert result.state == AuthState.AUTHENTICATED
    mock_client.sign_in.assert_awaited_once_with(
        phone="+77001234567",
        code="12345",
        phone_code_hash="hash_clean",
    )


