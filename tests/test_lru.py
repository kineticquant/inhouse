from __future__ import annotations

from inhouse.store import MISS, MemoryStore


def test_lru_evicts_least_recently_used_entry() -> None:
    cache = MemoryStore(max_size=2)
    cache.set("a", 1, 60)
    cache.set("b", 2, 60)
    cache.get("a")
    cache.set("c", 3, 60)

    assert cache.get("a") == 1
    assert cache.get("b") is MISS
    assert cache.get("c") == 3
    assert cache.size == 2
