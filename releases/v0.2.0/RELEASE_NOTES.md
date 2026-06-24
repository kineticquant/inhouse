# Release Notes

## inhouse-cache v0.2.0

**Keep hot data cheap to serve** — one layer deeper (memory → HTTP) with sensible defaults and no breaking changes.

Zero-dependency, in-process TTL cache for Python. Stampede-safe, LRU-bounded, with optional sliding TTL and FastAPI HTTP caching.

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

1. **Sliding TTL (`sliding=True`)** — Extends the lifespan of active cache entries on every successful read. Frequently accessed data (active sessions, hot config) stays warm; idle data still expires naturally.

2. **HTTP Cache-Control (`http_cache=True`)** — Offloads execution load entirely. If a client browser or a CDN (like Cloudflare) sees a valid `Cache-Control` header with `max-age`, they won't even send the request to your FastAPI server — saving bandwidth and compute. Defaults to `private`; opt in to `cache_visibility="public"` for CDN-shared assets.

3. **ETag + 304 Not Modified (`etag=True`)** — Generates a stable content hash and handles `If-None-Match` conditional requests. When the client already has the current version, inhouse returns `304 Not Modified` with an empty body instead of re-transmitting the full payload — a huge bandwidth win on repeat traffic. Fits between full cache skip and full refresh: after `max-age` expires, conditional requests avoid resending unchanged bodies.

4. **`remaining_ttl()` store API** — Exposes seconds-until-expiry for a key; powers accurate `max-age` headers and enables future integrations.

### Three layers, one story

| Layer | What it saves |
|---|---|
| In-process cache (v0.1.x) | Server compute on repeat hits |
| `Cache-Control` / `max-age` (v0.2.0) | The round trip entirely while fresh |
| ETag / 304 (v0.2.0) | The response payload when the round trip happens anyway |

### Quick start

```python
from inhouse import MemoryStore
from inhouse.fastapi import create_lifespan, fastapi_cache

store = MemoryStore(max_size=1024, default_ttl=60)
app = FastAPI(lifespan=create_lifespan(store))

@app.get("/items/{item_id}")
@fastapi_cache(
    60,
    store=store,
    sliding=True,
    http_cache=True,
    etag=True,
    cache_visibility="public",
)
async def get_item(item_id: int) -> dict[str, int]:
    return {"item_id": item_id}
```

### Migration

No breaking API changes. New parameters default to v0.1.x behavior:

- `sliding=False`
- `http_cache=False`
- `etag=False`
- `cache_visibility="private"`

### Requirements

- Python 3.10+
- MIT License

### Note

This is a **per-process** in-memory cache. Multi-worker deployments (e.g. `uvicorn --workers 4`) each maintain an independent cache — not a distributed cache.

HTTP cache headers (`Cache-Control`, ETag) are independent of in-process invalidation. Calling `store.delete()` or waiting for in-process expiry does not invalidate browser or CDN copies.

Full docs: https://github.com/kineticquant/inhouse
