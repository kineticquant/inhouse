from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from inhouse.store import MemoryStore
from inhouse.sweeper import ExpirySweeper


@asynccontextmanager
async def inhouse_lifespan(
    store: MemoryStore,
    *,
    sweep_interval: float = 30.0,
) -> AsyncIterator[None]:
    """FastAPI lifespan helper that starts and stops the expiry sweeper."""
    sweeper = ExpirySweeper(store, interval_seconds=sweep_interval)
    task = sweeper.start()
    try:
        yield
    finally:
        await sweeper.stop(task)


def create_lifespan(
    store: MemoryStore,
    *,
    sweep_interval: float = 30.0,
) -> Callable[[Any], AbstractAsyncContextManager[None]]:
    """Return a FastAPI-compatible lifespan callable bound to a cache store."""

    @asynccontextmanager
    async def lifespan(_app: Any) -> AsyncIterator[None]:
        async with inhouse_lifespan(store, sweep_interval=sweep_interval):
            yield

    return lifespan
