from __future__ import annotations

import time

from inhouse.decorator import cache
from inhouse.store import MemoryStore


def test_sync_decorator_caches_result() -> None:
    store = MemoryStore()
    calls = {"count": 0}

    @cache(60, store=store)
    def compute(value: int) -> int:
        calls["count"] += 1
        return value * 2

    assert compute(2) == 4
    assert compute(2) == 4
    assert calls["count"] == 1


def test_sync_decorator_respects_ttl() -> None:
    store = MemoryStore()
    calls = {"count": 0}

    @cache(0.05, store=store)
    def compute() -> int:
        calls["count"] += 1
        return calls["count"]

    assert compute() == 1
    assert compute() == 1
    time.sleep(0.06)
    assert compute() == 2
