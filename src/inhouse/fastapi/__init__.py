from __future__ import annotations

from inhouse.decorator import cache, inhouse_cache
from inhouse.fastapi.decorator import (
    configure_fastapi_default_store,
    fastapi_cache,
    get_fastapi_default_store,
)
from inhouse.fastapi.keys import make_fastapi_cache_key
from inhouse.fastapi.lifespan import create_lifespan, inhouse_lifespan

__all__ = [
    "cache",
    "configure_fastapi_default_store",
    "create_lifespan",
    "fastapi_cache",
    "get_fastapi_default_store",
    "inhouse_cache",
    "inhouse_lifespan",
    "make_fastapi_cache_key",
]
