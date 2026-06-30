"""inhouse — zero-dependency, in-process TTL cache with LRU eviction."""

from inhouse.decorator import (
    cache,
    caching_disabled,
    configure_default_store,
    disable_all,
    enable_all,
    get_default_store,
    inhouse_cache,
)
from inhouse.entry import CacheEntry
from inhouse.http_cache import (
    HttpCacheOutcome,
    cache_control_header,
    etag_for_value,
    etag_matches,
    http_cache_headers,
    http_cache_outcome,
)
from inhouse.keys import freeze_for_key, make_cache_key, make_weak_etag
from inhouse.store import MemoryStore
from inhouse.sweeper import ExpirySweeper

__all__ = [
    "CacheEntry",
    "ExpirySweeper",
    "HttpCacheOutcome",
    "MemoryStore",
    "cache",
    "cache_control_header",
    "caching_disabled",
    "configure_default_store",
    "disable_all",
    "enable_all",
    "etag_for_value",
    "etag_matches",
    "freeze_for_key",
    "get_default_store",
    "http_cache_headers",
    "http_cache_outcome",
    "inhouse_cache",
    "make_cache_key",
    "make_weak_etag",
]
__version__ = "0.3.0"
