from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from inhouse.decorator import cache, inhouse_cache
from inhouse.keys import make_cache_key
from inhouse.store import MemoryStore
from inhouse.sweeper import ExpirySweeper

# MUST have fastapi which uses starlette to work with RR tuple
try:
    from starlette.requests import Request
    from starlette.responses import Response

    _FASTAPI_EXCLUDE_TYPES: tuple[type[Any], ...] = (Request, Response)
except ImportError:  # pragma: no cover - optional dependency, technically
    _FASTAPI_EXCLUDE_TYPES = ()


def make_fastapi_cache_key(
    func: Any,
    args: Any,
    kwargs: Any,
    *,
    exclude_types: tuple[type[Any], ...] = (),
) -> str:
    merged_exclude = _FASTAPI_EXCLUDE_TYPES + exclude_types
    return make_cache_key(func, args, kwargs, exclude_types=merged_exclude)


def fastapi_cache(
    ttl_seconds: float | Callable[[], float] | None = None,
    *,
    store: MemoryStore | None = None,
) -> Callable[[Any], Any]:
    """Cache decorator that excludes Starlette Request/Response objects from keys."""
    return inhouse_cache(
        ttl_seconds,
        store=store,
        key_builder=make_fastapi_cache_key,
    )


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


__all__ = [
    "cache",
    "create_lifespan",
    "fastapi_cache",
    "inhouse_cache",
    "inhouse_lifespan",
    "make_fastapi_cache_key",
]
