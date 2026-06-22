from __future__ import annotations

import asyncio

from inhouse.store import MemoryStore


class ExpirySweeper:
    """Background task that periodically purges expired cache entries."""

    def __init__(self, store: MemoryStore, *, interval_seconds: float = 30.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._store = store
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self._interval_seconds)
            self._store.purge_expired()

    def start(self) -> asyncio.Task[None]:
        self._task = asyncio.create_task(self.run(), name="inhouse-expiry-sweeper")
        return self._task

    async def stop(self, task: asyncio.Task[None] | None = None) -> None:
        target = task or self._task
        if target is None:
            return
        target.cancel()
        try:
            await target
        except asyncio.CancelledError:
            pass
        if task is None:
            self._task = None
