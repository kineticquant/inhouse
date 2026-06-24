"""inhouse — zero-dependency, in-process TTL cache with LRU eviction."""

from inhouse.decorator import cache, configure_default_store, get_default_store, inhouse_cache
from inhouse.entry import CacheEntry
from inhouse.http_cache import (
    HttpCacheOutcome,
    cache_control_header,
    etag_for_value,
    etag_matches,
    http_cache_headers,
    http_cache_outcome,
)
from inhouse.keys import make_cache_key, make_weak_etag
from inhouse.store import MemoryStore
from inhouse.sweeper import ExpirySweeper

__all__ = [
    "CacheEntry",
    "ExpirySweeper",
    "HttpCacheOutcome",
    "MemoryStore",
    "cache",
    "cache_control_header",
    "configure_default_store",
    "etag_for_value",
    "etag_matches",
    "get_default_store",
    "http_cache_headers",
    "http_cache_outcome",
    "inhouse_cache",
    "make_cache_key",
    "make_weak_etag",
]
__version__ = "0.2.1"
