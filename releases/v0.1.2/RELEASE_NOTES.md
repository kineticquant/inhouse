# Release Notes

## inhouse-cache v0.1.2

Zero-dependency, in-process TTL cache for Python. Stampede-safe, LRU-bounded, with safer cache reads and more resilient async singleflight.

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

### Key Release Highlights

- **FastAPI integration package** — `inhouse.fastapi` is now a package (`keys`, `decorator`, `lifespan` submodules) establishing the `inhouse/<integration>/` pattern for future backends. Public imports are unchanged; core `keys` and `decorator` stay in `inhouse/`.
- **`MemoryStore(copy_on_read=True)`** — opt-in deep copy on `get()` so callers cannot mutate cached dicts/lists and corrupt state for other requests.
- **Type-qualified key fallback** — custom objects with identical `str()` representations no longer collide in cache keys; distinct types get distinct keys.
- **`@fastapi_cache(key_builder=...)`** — pass a custom key builder for domain objects or database models without fighting the default JSON encoder.
- **Async singleflight cancellation shield** — if the leader HTTP client disconnects mid-compute, the backend work continues and populates the cache for concurrent followers waiting on the same key.

### Quick start

```python
from inhouse import MemoryStore, inhouse_cache

store = MemoryStore(max_size=1024, default_ttl=60, copy_on_read=True)

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
