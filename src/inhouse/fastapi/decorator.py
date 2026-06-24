from __future__ import annotations

from collections.abc import Callable
from typing import Any

from inhouse.decorator import inhouse_cache
from inhouse.fastapi.keys import make_fastapi_cache_key
from inhouse.store import MemoryStore

TtlSource = float | Callable[[], float] | None


def fastapi_cache(
    ttl_seconds: TtlSource = None,
    *,
    store: MemoryStore | None = None,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Any], Any]:
    """Cache decorator that excludes Starlette Request/Response objects from keys."""
    return inhouse_cache(
        ttl_seconds,
        store=store,
        key_builder=key_builder or make_fastapi_cache_key,
    )
