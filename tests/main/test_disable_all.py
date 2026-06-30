from __future__ import annotations

from inhouse import MemoryStore, disable_all, enable_all, inhouse_cache
from inhouse.decorator import caching_disabled


def test_disable_all_bypasses_cache() -> None:
    enable_all()
    store = MemoryStore(default_ttl=60)
    calls = {"count": 0}

    @inhouse_cache(store=store)
    def compute(x: int) -> int:
        calls["count"] += 1
        return x

    assert compute(1) == 1
    assert compute(1) == 1
    assert calls["count"] == 1

    disable_all()
    assert caching_disabled() is True
    assert compute(1) == 1
    assert calls["count"] == 2

    enable_all()
    assert caching_disabled() is False
    assert compute(1) == 1
    assert calls["count"] == 2
