from __future__ import annotations

from inhouse.sqlite import query_store


def test_query_store_enables_copy_on_read() -> None:
    store = query_store(max_size=10, default_ttl=30)
    store.set("key", {"value": 1}, 30)
    copied = store.get("key")
    copied["value"] = 2
    assert store.get("key") == {"value": 1}
