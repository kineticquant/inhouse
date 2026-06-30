from __future__ import annotations

import inspect
import os
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from inhouse.files.watch import discover_paths, files_changed, snapshot_mtimes
from inhouse.http_cache import etag_for_value
from inhouse.keys import make_cache_key
from inhouse.singleflight import AsyncSingleflight, SyncSingleflight
from inhouse.store import MISS, MemoryStore

F = TypeVar("F", bound=Callable[..., Any])

TtlSource = float | Callable[[], float] | None

_DEFAULT_STORE = MemoryStore()
_ASYNC_SINGLEFLIGHT = AsyncSingleflight()
_SYNC_SINGLEFLIGHT = SyncSingleflight()
_disable_all = os.environ.get("INHOUSE_CACHE_DISABLE", "").lower() in ("1", "true", "yes")


def get_default_store() -> MemoryStore:
    return _DEFAULT_STORE


def configure_default_store(store: MemoryStore) -> None:
    global _DEFAULT_STORE
    _DEFAULT_STORE = store


def caching_disabled() -> bool:
    return _disable_all


def disable_all() -> None:
    global _disable_all
    _disable_all = True


def enable_all() -> None:
    global _disable_all
    _disable_all = False


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


def _key_prefix(func: Callable[..., Any]) -> str:
    return f"{func.__module__}.{func.__qualname__}:"


def _watched_paths(
    watch_files: bool | list[str],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> list[str]:
    return discover_paths(args, kwargs, watch_files)


def _cache_hit_is_stale(
    target_store: MemoryStore,
    cache_key: str,
    watch_files: bool | list[str],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> bool:
    if not watch_files:
        return False
    entry = target_store.get_entry(cache_key)
    if entry is None:
        return True
    paths = _watched_paths(watch_files, args, kwargs)
    if files_changed(entry.watch_mtimes, paths):
        target_store.delete(cache_key)
        return True
    return False


def _attach_cache_clear(
    wrapper: Callable[..., Any],
    func: Callable[..., Any],
    target_store: MemoryStore,
) -> None:
    wrapper.cache_clear = lambda: target_store.delete_prefix(_key_prefix(func))  # type: ignore[attr-defined]


# cache decorator for sync and async callables
def cache(
    ttl_seconds: TtlSource = None,
    *,
    store: MemoryStore | None = None,
    key_builder: Callable[..., str] = make_cache_key,
    exclude_types: tuple[type[Any], ...] = (),
    sliding: bool = False,
    etag: bool = False,
    watch_files: bool | list[str] = False,
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if _disable_all:
                    return await func(*args, **kwargs)

                target_store = store or _DEFAULT_STORE
                cache_key = key_builder(func, args, kwargs, exclude_types=exclude_types)

                cached = target_store.get(cache_key)
                if cached is not MISS and not _cache_hit_is_stale(
                    target_store, cache_key, watch_files, args, kwargs
                ):
                    return cached

                async def compute() -> Any:
                    recheck = target_store.get(cache_key)
                    if recheck is not MISS and not _cache_hit_is_stale(
                        target_store, cache_key, watch_files, args, kwargs
                    ):
                        return recheck
                    result = await func(*args, **kwargs)
                    paths = _watched_paths(watch_files, args, kwargs)
                    watch_mtimes = snapshot_mtimes(paths) if paths else None
                    target_store.set(
                        cache_key,
                        result,
                        _resolve_ttl(target_store, ttl_seconds),
                        sliding=sliding,
                        etag=etag_for_value(result, enabled=etag),
                        watch_mtimes=watch_mtimes,
                    )
                    return result

                return await _ASYNC_SINGLEFLIGHT.do(cache_key, compute)

            _attach_cache_clear(async_wrapper, func, store or _DEFAULT_STORE)
            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if _disable_all:
                return func(*args, **kwargs)

            target_store = store or _DEFAULT_STORE
            cache_key = key_builder(func, args, kwargs, exclude_types=exclude_types)

            cached = target_store.get(cache_key)
            if cached is not MISS and not _cache_hit_is_stale(
                target_store, cache_key, watch_files, args, kwargs
            ):
                return cached

            def compute() -> Any:
                recheck = target_store.get(cache_key)
                if recheck is not MISS and not _cache_hit_is_stale(
                    target_store, cache_key, watch_files, args, kwargs
                ):
                    return recheck
                result = func(*args, **kwargs)
                paths = _watched_paths(watch_files, args, kwargs)
                watch_mtimes = snapshot_mtimes(paths) if paths else None
                target_store.set(
                    cache_key,
                    result,
                    _resolve_ttl(target_store, ttl_seconds),
                    sliding=sliding,
                    etag=etag_for_value(result, enabled=etag),
                    watch_mtimes=watch_mtimes,
                )
                return result

            return _SYNC_SINGLEFLIGHT.do(cache_key, compute)

        _attach_cache_clear(sync_wrapper, func, store or _DEFAULT_STORE)
        return sync_wrapper  # type: ignore[return-value]

    return decorator


inhouse_cache = cache
