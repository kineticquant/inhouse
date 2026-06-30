from __future__ import annotations

import copy
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from inhouse.entry import CacheEntry


class _CacheMiss:
    """Sentinel returned when a key is absent or expired."""


MISS = _CacheMiss()


class MemoryStore:
    """Thread-safe in-memory cache with TTL expiry and LRU eviction."""

    def __init__(
        self,
        max_size: int = 1024,
        *,
        default_ttl: float | None = None,
        copy_on_read: bool = False,
        copy_fn: Callable[[Any], Any] | None = None,
        sliding: bool = False,
    ) -> None:
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._copy_on_read = copy_on_read
        self._copy_fn = copy_fn
        self._sliding = sliding
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        if default_ttl is not None and default_ttl <= 0:
            raise ValueError("default_ttl must be positive")

    @property
    def max_size(self) -> int:
        return self._max_size

    @property
    def default_ttl(self) -> float | None:
        with self._lock:
            return self._default_ttl

    @default_ttl.setter
    def default_ttl(self, value: float | None) -> None:
        if value is not None and value <= 0:
            raise ValueError("default_ttl must be positive")
        with self._lock:
            self._default_ttl = value

    @property
    def sliding(self) -> bool:
        with self._lock:
            return self._sliding

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def _copy_value(self, value: Any) -> Any:
        if self._copy_fn is not None:
            return self._copy_fn(value)
        return copy.deepcopy(value)

    def get(self, key: str, *, default: Any = MISS) -> Any:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return default
            now = time.monotonic()
            if now >= entry.expires_at:
                del self._entries[key]
                return default
            if entry.sliding:
                entry.expires_at = now + entry.ttl_seconds
            self._entries.move_to_end(key)
            value = entry.value
            if self._copy_on_read:
                return self._copy_value(value)
            return value

    def get_entry(self, key: str) -> CacheEntry | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if time.monotonic() >= entry.expires_at:
                del self._entries[key]
                return None
            return entry

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: float | None = None,
        *,
        sliding: bool | None = None,
        etag: str | None = None,
        watch_mtimes: dict[str, float] | None = None,
    ) -> None:
        with self._lock:
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            if ttl is None or ttl <= 0:
                raise ValueError("ttl_seconds must be positive")
            use_sliding = self._sliding if sliding is None else sliding
            expires_at = time.monotonic() + ttl
            self._entries[key] = CacheEntry(
                expires_at=expires_at,
                value=value,
                ttl_seconds=ttl,
                sliding=use_sliding,
                etag=etag,
                watch_mtimes=watch_mtimes,
            )
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_size:
                self._entries.popitem(last=False)

    # (remaining_ttl, etag) for a live entry, or none if missing/expired
    def entry_meta(self, key: str) -> tuple[float, str | None] | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            now = time.monotonic()
            if now >= entry.expires_at:
                return None
            return max(0.0, entry.expires_at - now), entry.etag

    def remaining_ttl(self, key: str) -> float | None:
        meta = self.entry_meta(key)
        return meta[0] if meta is not None else None

    def get_etag(self, key: str) -> str | None:
        meta = self.entry_meta(key)
        return meta[1] if meta is not None else None

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                return True
            return False

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [key for key in self._entries if key.startswith(prefix)]
            for key in keys:
                del self._entries[key]
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    # remove expired entries; returns count removed
    def purge_expired(self) -> int:
        now = time.monotonic()
        removed = 0
        with self._lock:
            expired_keys = [key for key, entry in self._entries.items() if now >= entry.expires_at]
            for key in expired_keys:
                del self._entries[key]
                removed += 1
        return removed

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._entries.keys())
