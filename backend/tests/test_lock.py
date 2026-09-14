"""
Unit tests for distributed RedisLock concurrency control.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery

from app.bot.handlers import cb_run_clean, cb_run_scan
from app.telegram.lock import RedisLock


@pytest.mark.asyncio
async def test_redis_lock_acquire_and_release_success():
    """Verify lock is atomically acquired with SETNX and deleted on context exit."""
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)

    lock = RedisLock(mock_redis, "scan:12345", timeout=300)
    async with lock as acquired:
        assert acquired is True
        mock_redis.set.assert_awaited_once_with(
            "lock:scan:12345", "1", ex=300, nx=True
        )
        # Lock is still held, delete not called yet
        mock_redis.delete.assert_not_awaited()

    # Once context exits, delete must be awaited
    mock_redis.delete.assert_awaited_once_with("lock:scan:12345")


@pytest.mark.asyncio
async def test_redis_lock_contention_already_held():
    """Verify lock acquisition fails when key already exists in Redis (NX condition fails)."""
    mock_redis = AsyncMock()
    # SET with nx=True returns None when key already exists
    mock_redis.set = AsyncMock(return_value=None)
    mock_redis.delete = AsyncMock()

    lock = RedisLock(mock_redis, "clean:12345", timeout=600)
    async with lock as acquired:
        assert acquired is False
        mock_redis.set.assert_awaited_once_with(
            "lock:clean:12345", "1", ex=600, nx=True
        )

    # Delete must NOT be called if lock was never acquired
    mock_redis.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_lock_ttl_expiration_simulation():
    """
    Simulate crash / lock expiry:
    Process 1 acquires lock with TTL, terminates abnormally without releasing.
    After TTL expires in Redis, Process 2 can successfully acquire the lock.
    """
    # In-memory simulated Redis KV store with expiry
    store: dict[str, str] = {}

    class FakeRedis:
        async def set(
            self, key: str, val: str, ex: int | None = None, nx: bool = False
        ) -> bool | None:
            if nx and key in store:
                return None
            store[key] = val
            return True

        async def delete(self, key: str) -> int:
            return 1 if store.pop(key, None) is not None else 0

    fake_redis = FakeRedis()

    # Process 1 acquires lock but 'crashes' (no __aexit__)
    lock1 = RedisLock(fake_redis, "user:777", timeout=2)
    acq1 = await lock1.__aenter__()
    assert acq1 is True
    assert "lock:user:777" in store

    # Process 2 tries immediately and fails
    lock2 = RedisLock(fake_redis, "user:777", timeout=2)
    async with lock2 as acq2:
        assert acq2 is False

    # Simulate TTL expiration (key evicted by Redis after timeout)
    del store["lock:user:777"]

    # Process 2 tries again after TTL expiration and succeeds
    lock3 = RedisLock(fake_redis, "user:777", timeout=2)
    async with lock3 as acq3:
        assert acq3 is True
        assert "lock:user:777" in store

    # Process 3 released cleanly
    assert "lock:user:777" not in store


@pytest.mark.asyncio
async def test_redis_lock_exception_resilience():
    """Verify Redis connection error in acquire does not crash caller."""
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(side_effect=ConnectionError("Redis down"))
    mock_redis.delete = AsyncMock(side_effect=ConnectionError("Redis down"))

    lock = RedisLock(mock_redis, "key_err")
    async with lock as acquired:
        assert acquired is False

    mock_redis.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_handler_run_scan_lock_contention():
    """Verify cb_run_scan returns early with localized alert if scan is already locked."""
    mock_cb = AsyncMock(spec=CallbackQuery)
    mock_cb.from_user = MagicMock(id=98765)
    mock_cb.answer = AsyncMock()
    mock_state = AsyncMock()

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=None)

    await cb_run_scan(mock_cb, mock_state, redis=mock_redis, lang="ru")
    mock_cb.answer.assert_awaited_once_with(
        "⏳ Операция уже выполняется, пожалуйста, подождите.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_handler_run_clean_lock_contention():
    """Verify cb_run_clean returns early with localized alert if clean is already locked."""
    mock_cb = AsyncMock(spec=CallbackQuery)
    mock_cb.from_user = MagicMock(id=98765)
    mock_cb.answer = AsyncMock()
    mock_state = AsyncMock()

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=None)

    await cb_run_clean(mock_cb, mock_state, redis=mock_redis, lang="kk")
    mock_cb.answer.assert_awaited_once_with(
        "⏳ Бұл әрекет қазір орындалуда, күте тұрыңыз.",
        show_alert=True,
    )
