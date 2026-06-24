from __future__ import annotations

import asyncio
import threading

import pytest

from inhouse.decorator import cache
from inhouse.store import MemoryStore


@pytest.mark.asyncio
async def test_async_stampede_runs_backend_once() -> None:
    store = MemoryStore()
    calls = {"count": 0}
    started = asyncio.Event()
    release = asyncio.Event()

    @cache(60, store=store)
    async def expensive() -> str:
        calls["count"] += 1
        started.set()
        await release.wait()
        return "done"

    async def invoke() -> str:
        return await expensive()

    tasks = [asyncio.create_task(invoke()) for _ in range(50)]
    await started.wait()
    release.set()
    results = await asyncio.gather(*tasks)

    assert all(result == "done" for result in results)
    assert calls["count"] == 1


def test_sync_stampede_runs_backend_once() -> None:
    store = MemoryStore()
    calls = {"count": 0}
    started = threading.Event()
    release = threading.Event()

    @cache(60, store=store)
    def expensive() -> str:
        calls["count"] += 1
        started.set()
        release.wait(timeout=5)
        return "done"

    threads = [threading.Thread(target=expensive) for _ in range(50)]
    for thread in threads:
        thread.start()

    started.wait(timeout=5)
    release.set()
    for thread in threads:
        thread.join(timeout=5)

    assert calls["count"] == 1
