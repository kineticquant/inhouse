from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from inhouse.keys import make_cache_key
from inhouse.singleflight import AsyncSingleflight, SyncSingleflight
from inhouse.store import MISS, MemoryStore

F = TypeVar("F", bound=Callable[..., Any])

TtlSource = float | Callable[[], float] | None

_DEFAULT_STORE = MemoryStore()
_ASYNC_SINGLEFLIGHT = AsyncSingleflight()
_SYNC_SINGLEFLIGHT = SyncSingleflight()


def get_default_store() -> MemoryStore:
    return _DEFAULT_STORE


def configure_default_store(store: MemoryStore) -> None:
    global _DEFAULT_STORE
    _DEFAULT_STORE = store


def _resolve_ttl(target_store: MemoryStore, ttl_seconds: TtlSource) -> float:
    if callable(ttl_seconds):
        resolved = ttl_seconds()
    elif ttl_seconds is not None:
        resolved = ttl_seconds
    elif target_store.default_ttl is not None:
        resolved = target_store.default_ttl
    else:
        raise ValueError("ttl_seconds is required when the store has no default_ttl")

    if resolved <= 0:
        raise ValueError("ttl_seconds must be positive")
    return resolved


# cache decorator for sync and async callables
def cache(ttl_seconds: TtlSource = None, *, store: MemoryStore | None = None, key_builder: Callable[..., str] = make_cache_key, exclude_types: tuple[type[Any], ...] = (), sliding: bool = False) -> Callable[[F], F]:  # noqa: E501

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                target_store = store or _DEFAULT_STORE
                cache_key = key_builder(
                    func,
                    args,
                    kwargs,
                    exclude_types=exclude_types,
                )

                cached = target_store.get(cache_key)
                if cached is not MISS:
                    return cached

                async def compute() -> Any:
                    recheck = target_store.get(cache_key)
                    if recheck is not MISS:
                        return recheck
                    result = await func(*args, **kwargs)
                    ttl = _resolve_ttl(target_store, ttl_seconds)
                    target_store.set(cache_key, result, ttl, sliding=sliding)
                    return result

                return await _ASYNC_SINGLEFLIGHT.do(cache_key, compute)

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            target_store = store or _DEFAULT_STORE
            cache_key = key_builder(
                func,
                args,
                kwargs,
                exclude_types=exclude_types,
            )

            cached = target_store.get(cache_key)
            if cached is not MISS:
                return cached

            def compute() -> Any:
                recheck = target_store.get(cache_key)
                if recheck is not MISS:
                    return recheck
                result = func(*args, **kwargs)
                ttl = _resolve_ttl(target_store, ttl_seconds)
                target_store.set(cache_key, result, ttl, sliding=sliding)
                return result

            return _SYNC_SINGLEFLIGHT.do(cache_key, compute)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


inhouse_cache = cache
