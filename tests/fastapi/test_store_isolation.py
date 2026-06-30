from __future__ import annotations

from inhouse import MemoryStore, configure_default_store, inhouse_cache
from inhouse.fastapi import (
    configure_fastapi_default_store,
    fastapi_cache,
    get_fastapi_default_store,
)


def test_fastapi_default_store_is_isolated_from_core() -> None:
    core_store = MemoryStore(default_ttl=60)
    fastapi_store = MemoryStore(default_ttl=60)
    configure_default_store(core_store)
    configure_fastapi_default_store(fastapi_store)

    @inhouse_cache(store=core_store)
    def core_fn(x: int) -> int:
        return x

    @fastapi_cache(store=fastapi_store)
    def route_fn(x: int) -> int:
        return x

    core_fn(1)
    route_fn(1)

    assert core_store.size == 1
    assert fastapi_store.size == 1
    assert get_fastapi_default_store() is fastapi_store
