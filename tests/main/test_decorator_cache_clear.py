from __future__ import annotations

from inhouse import MemoryStore, inhouse_cache


def test_cache_clear_removes_only_decorated_function_keys() -> None:
    store = MemoryStore(default_ttl=60)
    calls = {"a": 0, "b": 0}

    @inhouse_cache(store=store)
    def fn_a(x: int) -> int:
        calls["a"] += 1
        return x * 2

    @inhouse_cache(store=store)
    def fn_b(x: int) -> int:
        calls["b"] += 1
        return x + 1

    assert fn_a(1) == 2
    assert fn_b(1) == 2
    assert calls == {"a": 1, "b": 1}

    fn_a.cache_clear()
    assert fn_a(1) == 2
    assert fn_b(1) == 2
    assert calls == {"a": 2, "b": 1}
