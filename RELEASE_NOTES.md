# Release Notes

## inhouse-cache v0.1.1 — Initial release

Zero-dependency, in-process TTL cache for Python. One decorator, stampede-safe, LRU-bounded. For when Redis is a meeting you don't want to have.

### Install

```bash
pip install inhouse-cache
```

FastAPI helpers (`fastapi_cache`, lifespan sweeper):

```bash
pip install inhouse-cache[fastapi]
```

Imports use `inhouse`:

```python
from inhouse import MemoryStore, inhouse_cache
```

### Highlights

- **Zero runtime dependencies** in the core package
- TTL cache with lazy expiry on read
- LRU eviction when `max_size` is exceeded
- Per-key singleflight stampede guard — concurrent misses on the same key coalesce to one computation
- Deterministic cache keys via canonical JSON serialization
- Thread-safe store for sync and async callables
- Fixed, store-default, or callable TTL per cache write
- Optional FastAPI extra: `@fastapi_cache`, Request/Response-aware keys, background expiry sweeper

### Quick start

```python
from inhouse import MemoryStore, inhouse_cache

store = MemoryStore(max_size=1024, default_ttl=60)

@inhouse_cache(store=store)
async def load_user(user_id: int) -> dict[str, int]:
    return {"user_id": user_id}
```

### Requirements

- Python 3.10+
- MIT License

### Note

This is a **per-process** in-memory cache. Multi-worker deployments (e.g. `uvicorn --workers 4`) each maintain an independent cache — not a distributed cache.

Full docs: https://github.com/kineticquant/inhouse
