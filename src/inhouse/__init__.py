"""inhouse — zero-dependency, in-process TTL cache with LRU eviction."""

from inhouse.decorator import cache, configure_default_store, get_default_store, inhouse_cache
from inhouse.entry import CacheEntry
from inhouse.keys import make_cache_key
from inhouse.store import MemoryStore
from inhouse.sweeper import ExpirySweeper

__all__ = [
    "CacheEntry",
    "ExpirySweeper",
    "MemoryStore",
    "cache",
    "configure_default_store",
    "get_default_store",
    "inhouse_cache",
    "make_cache_key",
]
__version__ = "0.1.0"
