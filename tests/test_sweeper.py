from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from inhouse.store import MISS, MemoryStore
from inhouse.sweeper import ExpirySweeper


@pytest.mark.asyncio
async def test_sweeper_run_purges_expired_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MemoryStore()
    base = 1000.0

    with patch("inhouse.store.time.monotonic", return_value=base):
        store.set("stale", "old", 1)
        store.set("fresh", "ok", 3600)

    sweeper = ExpirySweeper(store, interval_seconds=0.01)
    iterations = {"count": 0}

    async def fake_sleep(_seconds: float) -> None:
        iterations["count"] += 1
        if iterations["count"] >= 1:
            raise asyncio.CancelledError

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with patch("inhouse.store.time.monotonic", return_value=base + 10):
        with pytest.raises(asyncio.CancelledError):
            await sweeper.run()

        assert store.get("stale") is MISS
        assert store.get("fresh") == "ok"


@pytest.mark.asyncio
async def test_sweeper_stop_cancels_background_task() -> None:
    store = MemoryStore()
    sweeper = ExpirySweeper(store, interval_seconds=60.0)
    task = sweeper.start()
    await sweeper.stop(task)
    assert task.cancelled() or task.done()
