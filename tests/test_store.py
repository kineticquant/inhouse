from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from inhouse.store import MISS, MemoryStore


def test_set_and_get_returns_value() -> None:
    cache = MemoryStore(max_size=10)
    cache.set("key", "value", 60)
    assert cache.get("key") == "value"


def test_get_missing_key_returns_miss_sentinel() -> None:
    cache = MemoryStore()
    assert cache.get("missing") is MISS


def test_get_with_custom_default() -> None:
    cache = MemoryStore()
    assert cache.get("missing", default="fallback") == "fallback"


def test_expired_entry_is_removed_on_read() -> None:
    cache = MemoryStore()
    cache.set("key", "value", 60)

    with patch("inhouse.store.time.monotonic", return_value=time.monotonic() + 120):
        assert cache.get("key") is MISS
        assert cache.size == 0


def test_overwrite_updates_value() -> None:
    cache = MemoryStore()
    cache.set("key", "first", 60)
    cache.set("key", "second", 60)
    assert cache.get("key") == "second"


def test_delete_and_clear() -> None:
    cache = MemoryStore()
    cache.set("a", 1, 60)
    cache.set("b", 2, 60)
    assert cache.delete("a") is True
    assert cache.delete("a") is False
    assert cache.get("b") == 2
    cache.clear()
    assert cache.size == 0


def test_set_rejects_non_positive_ttl() -> None:
    cache = MemoryStore()
    with pytest.raises(ValueError):
        cache.set("key", "value", 0)


def test_default_ttl_on_store() -> None:
    cache = MemoryStore(default_ttl=60)
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_default_ttl_can_be_changed_at_runtime() -> None:
    cache = MemoryStore(default_ttl=60)
    cache.default_ttl = 120
    cache.set("key", "value")
    assert cache.default_ttl == 120


def test_cache_none_value() -> None:
    cache = MemoryStore()
    cache.set("key", None, 60)
    assert cache.get("key") is None
    assert cache.size == 1


def test_purge_expired() -> None:
    cache = MemoryStore()
    cache.set("fresh", "ok", 60)
    cache.set("stale", "old", 60)

    with patch("inhouse.store.time.monotonic", return_value=time.monotonic() + 120):
        removed = cache.purge_expired()

    assert removed == 2
    assert cache.size == 0
