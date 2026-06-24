from __future__ import annotations

import asyncio
import threading

import pytest

from inhouse.singleflight import AsyncSingleflight, SyncSingleflight


@pytest.mark.asyncio
async def test_async_singleflight_exception_propagates_to_followers() -> None:
    singleflight = AsyncSingleflight()
    in_compute = asyncio.Event()
    release = asyncio.Event()

    async def compute() -> str:
        in_compute.set()
        await release.wait()
        raise ValueError("boom")

    async def invoke() -> str:
        return await singleflight.do("key", compute)

    leader = asyncio.create_task(invoke())
    await in_compute.wait()
    follower = asyncio.create_task(invoke())
    await asyncio.sleep(0)
    release.set()

    with pytest.raises(ValueError, match="boom"):
        await leader
    with pytest.raises(ValueError, match="boom"):
        await follower

    assert singleflight._inflight == {}


@pytest.mark.asyncio
async def test_async_singleflight_leader_cancel_followers_still_succeed() -> None:
    singleflight = AsyncSingleflight()
    started = asyncio.Event()
    release = asyncio.Event()

    async def compute() -> str:
        started.set()
        await release.wait()
        return "ok"

    async def invoke() -> str:
        return await singleflight.do("key", compute)

    leader = asyncio.create_task(invoke())
    await started.wait()
    follower = asyncio.create_task(invoke())
    await asyncio.sleep(0)

    leader.cancel()

    with pytest.raises(asyncio.CancelledError):
        await leader

    release.set()
    assert await follower == "ok"
    assert singleflight._inflight == {}


def test_sync_singleflight_exception_propagates_to_followers() -> None:
    singleflight = SyncSingleflight()
    started = threading.Event()
    errors: list[BaseException] = []

    def compute() -> str:
        started.set()
        raise ValueError("boom")

    def invoke() -> None:
        try:
            singleflight.do("key", compute)
        except ValueError as exc:
            errors.append(exc)

    leader = threading.Thread(target=invoke)
    leader.start()
    started.wait(timeout=5)
    follower = threading.Thread(target=invoke)
    follower.start()
    leader.join(timeout=5)
    follower.join(timeout=5)

    assert len(errors) == 2
    assert all(str(exc) == "boom" for exc in errors)
    assert singleflight._inflight == {}
