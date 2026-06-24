# Release Notes

## inhouse-cache v0.2.1

**Fix:** HTTP cache semantics (ETag, `Cache-Control`, 304 decisions) now live in zero-dependency core. FastAPI keeps native Starlette responses; other frameworks can wire the same behavior without the FastAPI extra.

Zero-dependency, in-process TTL cache for Python. Stampede-safe, LRU-bounded, with optional sliding TTL and HTTP caching.

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
from inhouse import MemoryStore, http_cache_outcome, inhouse_cache
```

### Key Release Highlights

1. **`inhouse.http_cache` (core)** — Framework-agnostic helpers: `make_weak_etag`, `etag_matches`, `cache_control_header`, `http_cache_headers`, `http_cache_outcome`, and `HttpCacheOutcome`. No Starlette/FastAPI import required.

2. **`@inhouse_cache(etag=True)`** — Core decorator now stores weak ETag metadata at write time (`store.get_etag(key)` / `entry_meta`). Use with `http_cache_outcome` in Flask, Django, raw ASGI, etc.

3. **FastAPI extra unchanged for users** — `@fastapi_cache(http_cache=True, etag=True)` behaves the same: native `JSONResponse` / `304 Response`, `jsonable_encoder`, `Request` injection for `If-None-Match`. Internally delegates to core `http_cache_outcome` (no duplicated cache semantics).

### Quick start (core, any framework)

```python
from inhouse import MemoryStore, http_cache_outcome, inhouse_cache, make_cache_key

store = MemoryStore(default_ttl=60)

@inhouse_cache(60, store=store, etag=True)
async def load_item(item_id: int) -> dict[str, int]:
    return {"item_id": item_id}

body = await load_item(1)
key = make_cache_key(load_item, (1,), {})
outcome = http_cache_outcome(
    body,
    if_none_match=client_if_none_match,
    remaining_ttl=store.remaining_ttl(key),
    stored_etag=store.get_etag(key),
    http_cache=True,
    cache_visibility="public",
    use_etag=True,
)
# outcome.status_code, outcome.headers, outcome.body → your framework's response
```

### Migration

No breaking API changes from v0.2.0. New core exports are additive:

- `from inhouse import etag_matches, http_cache_outcome, make_weak_etag, ...`
- `@inhouse_cache(..., etag=True)` defaults to `False`

### Requirements

- Python 3.10+
- MIT License

### Note

This is a **per-process** in-memory cache. Multi-worker deployments (e.g. `uvicorn --workers 4`) each maintain an independent cache — not a distributed cache.

Full docs: https://github.com/kineticquant/inhouse
