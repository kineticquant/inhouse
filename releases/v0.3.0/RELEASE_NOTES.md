# Release Notes

## inhouse-cache v0.3.0

**Cache the work you repeat** — SQLite reads, RAG context assembly, file-backed system prompts — without Redis and without new third-party dependencies.

**Zero-dependency core** — still no runtime packages in `pip install inhouse-cache`. Stampede-safe, LRU-bounded, sync/async unified decorator. v0.3.0 adds keys, invalidation, file watching, and three vertical subpackages (`inhouse.sqlite`, `inhouse.rag`, `inhouse.files`) that also use **stdlib only** (`sqlite3`, `os`, `fnmatch`). Same wheel — no `[sqlite]` / `[rag]` / `[files]` pip extras.

**Optional FastAPI extra** (`pip install inhouse-cache[fastapi]`) — the only supported third-party add-on; requires `fastapi` / Starlette at import time. Unchanged for existing users.

### Install

```bash
pip install inhouse-cache
```

```python
from inhouse import MemoryStore, disable_all, freeze_for_key, inhouse_cache
from inhouse.sqlite import query_store, safe_copy
from inhouse.rag import rag_cache
from inhouse.files import file_cache
```

FastAPI helpers (unchanged):

```bash
pip install inhouse-cache[fastapi]
```

---

### Headline technical wins

These are the APIs and mechanisms worth upgrading for.

| Win | API / mechanism | Why it matters |
|---|---|---|
| **Recursive key freezing** | `freeze_for_key()`, updated `make_cache_key()` | Stable keys for `set`, nested `dict`, `list` vs `tuple`, `dataclass`, and Pydantic-like models (duck-typed, zero-dep) without JSON-serializing live objects at the call site |
| **Per-function invalidation** | `func.cache_clear()` → `MemoryStore.delete_prefix()` | Purge every entry for one decorated function after ingestion, config reload, or corpus update — no full `store.clear()` |
| **Global dev bypass** | `disable_all()`, `enable_all()`, `caching_disabled()`, `INHOUSE_CACHE_DISABLE` | Turn off all decorators process-wide while prompt-engineering or debugging; env var for local shells |
| **Lazy file invalidation** | `@inhouse_cache(watch_files=...)`, `CacheEntry.watch_mtimes` | `os.path.getmtime` on cache hit; auto-bust when markdown/txt prompts change on disk |
| **FastAPI store isolation** | `get_fastapi_default_store()` / `configure_fastapi_default_store()` vs core `get_default_store()` | `@fastapi_cache` and `@inhouse_cache` use **separate default `MemoryStore` backends** — HTTP traffic won't LRU-evict app data; pass one shared `store=` to enforce a global budget |
| **Pluggable copy-on-read** | `MemoryStore(copy_on_read=True, copy_fn=...)` | Hook custom copy logic at read time; sqlite vertical plugs in `safe_copy` for `sqlite3.Row` → `dict` fallback |
| **SQLite query caching** | `inhouse.sqlite`: `query_store()`, `safe_copy()`, `rows_to_dicts()` | `copy_on_read` preset for read-heavy SQL; Row mutate-protection without leaking C-objects into caller mutations |
| **RAG prompt caching** | `inhouse.rag`: `rag_cache()` | 600s TTL preset over `@inhouse_cache`; pair with `corpus_version` arg or `cache_clear()` after ingestion |
| **File / skill prompt caching** | `inhouse.files`: `file_cache()`, `discover_paths()`, `snapshot_mtimes()`, `files_changed()` | Long TTL + `watch_files` preset for `.md`/`.txt` system prompts and AI skills |
| **Unified sync/async decorator** | `@inhouse_cache` / `cache()` via `inspect.iscoroutinefunction` | One decorator for sync SQLite queries and async RAG compilation — unchanged API surface |
| **Zero-dep verticals** | `inhouse.sqlite`, `inhouse.rag`, `inhouse.files` | Always in the wheel, stdlib-only at runtime; no new PyPI dependencies beyond optional `[fastapi]` |

**Breaking (keys only):** v0.3.0 key digests differ from v0.2.x for some argument shapes (sets, list vs tuple, dataclass/model inputs). Expect **cache misses** after upgrade — not stale hits from old digests.

---

### Core APIs in detail

#### `freeze_for_key()` — recursive freezing before hash

Arguments are frozen, then hashed via the existing canonical JSON + SHA-256 pipeline:

- `list` → tagged tuple (`__list__`)
- `tuple` → tagged tuple (`__tuple__`) — **distinct from list**
- `set` / `frozenset` → `frozenset` of frozen children
- `dict` / `Mapping` → sorted `tuple` of `(str(key), frozen_value)` pairs
- `dataclass` instances → `("dataclass", qualname, field values…)`
- Pydantic v1/v2 duck-type → `("pydantic", qualname, frozen dump)` — **no `pydantic` import required**
- everything else → existing `module.qualname:str(value)` fallback

```python
from inhouse import freeze_for_key, make_cache_key, inhouse_cache

@inhouse_cache(60)
async def search(filters: dict[str, set[str]]) -> list[dict]:
    ...

# {"tags": {"ai", "cache"}} and {"tags": {"cache", "ai"}} → same cache key
```

#### `cache_clear()`, `delete_prefix()`, and ingestion workflows

Every `@inhouse_cache`-decorated function exposes `.cache_clear()` (same ergonomics as `functools.lru_cache`). Internally deletes keys prefixed with `{module}.{qualname}:`.

```python
compile_rag_prompt.cache_clear()  # after document ingestion
```

#### `disable_all()` and `INHOUSE_CACHE_DISABLE`

Module-level switch checked on every wrapper entry. When active: no `store.get`, no `store.set`, no singleflight — straight through to the underlying function.

```bash
INHOUSE_CACHE_DISABLE=1 uvicorn app:main
```

```python
from inhouse import disable_all, enable_all, caching_disabled

disable_all()
assert caching_disabled()
enable_all()
```

#### `watch_files` — three modes

| Value | Behavior |
|---|---|
| `False` | default — no file watching |
| `True` | walk `args`/`kwargs`; collect `str` paths where `os.path.isfile` |
| `["*.md", "*.txt"]` | discover paths in arguments, filter by `fnmatch` on basename |
| `["/abs/or/rel/path.md"]` | explicit static paths, even if not passed at call time |

On write: `snapshot_mtimes(paths)` stored on `CacheEntry.watch_mtimes`. On hit: any missing file or mtime mismatch → `store.delete(key)`, recompute.

```python
@inhouse_cache(3600, watch_files=["*.md"])
def load_prompt(path: str) -> str: ...
```

#### FastAPI ↔ core namespace separation

```python
from inhouse import get_default_store, configure_default_store
from inhouse.fastapi import (
    get_fastapi_default_store,
    configure_fastapi_default_store,
    fastapi_cache,
)

assert get_default_store() is not get_fastapi_default_store()  # isolated by default

shared = MemoryStore(max_size=2048, default_ttl=60)
configure_default_store(shared)
configure_fastapi_default_store(shared)  # opt-in shared budget
```

#### `MemoryStore(copy_fn=...)` + `copy_on_read`

```python
store = MemoryStore(copy_on_read=True, copy_fn=my_copy_fn)
# or use the sqlite preset:
from inhouse.sqlite import query_store
store = query_store(default_ttl=60)  # copy_fn=safe_copy built in
```

`safe_copy()` tries `copy.deepcopy`; on `TypeError`, converts `sqlite3.Row` → `dict` and deep-copies that. `rows_to_dicts()` for mapping results inside query functions on hot paths.

---

### Vertical packages — recipes

#### `inhouse.sqlite`

Cache query **results** in memory, not SQLite-as-store. Pure-signature query functions: obtain `db` from thread-local or pool, **not** as a decorated argument.

```python
import threading
import sqlite3

from inhouse import inhouse_cache
from inhouse.sqlite import query_store, rows_to_dicts

store = query_store(default_ttl=60)
_local = threading.local()

def get_db() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        _local.conn = sqlite3.connect("app.db")
        _local.conn.row_factory = sqlite3.Row
    return _local.conn

@inhouse_cache(store=store)
def fetch_settings(user_id: int) -> dict | None:
    row = get_db().execute(
        "SELECT * FROM settings WHERE user_id = ?", (user_id,)
    ).fetchone()
    return rows_to_dicts(row) if row else None
```

#### `inhouse.rag`

Cache compiled prompt strings. **Context versioning:** pass `corpus_version` (timestamp, hash, migration id) as an argument for automatic miss on corpus change. **Programmatic eviction:** `compile_prompt.cache_clear()` after ingestion.

```python
from inhouse.rag import rag_cache

@rag_cache(ttl_seconds=600)
async def compile_prompt(
    user_query: str,
    filters: dict,
    corpus_version: str,
) -> str:
    context = await vector_search(user_query, filters)
    return f"Context:\n{context}\n\nQuestion: {user_query}"

compile_prompt.cache_clear()
```

#### `inhouse.files`

```python
from inhouse.files import file_cache

@file_cache(ttl_seconds=3600, watch_files=["*.md"])
def load_skill(path: str) -> str:
    return open(path, encoding="utf-8").read()
```

Low-level helpers available for custom wiring: `discover_paths()`, `snapshot_mtimes()`, `files_changed()`.

---

### New exports — quick reference

**Core (`from inhouse import …`)**

| Symbol | Role |
|---|---|
| `freeze_for_key` | inspect/test frozen key material |
| `disable_all`, `enable_all`, `caching_disabled` | global cache bypass |
| `inhouse_cache(..., watch_files=)` | decorator with file mtime invalidation |
| `wrapper.cache_clear` | per-function invalidation (on decorated callables) |

**Store**

| Method / param | Role |
|---|---|
| `delete_prefix(prefix) -> int` | bulk delete by key prefix |
| `copy_fn` | custom copy when `copy_on_read=True` |
| `set(..., watch_mtimes=...)` | persist file snapshots on write |
| `get_entry(key)` | entry introspection incl. `watch_mtimes` |

**FastAPI (`from inhouse.fastapi import …`)**

| Symbol | Role |
|---|---|
| `get_fastapi_default_store` | isolated HTTP route cache backend |
| `configure_fastapi_default_store` | replace FastAPI default store |

**Vertical (opt-in import, same wheel)**

| Package | Key symbols |
|---|---|
| `inhouse.sqlite` | `query_store`, `safe_copy`, `rows_to_dicts` |
| `inhouse.rag` | `rag_cache` |
| `inhouse.files` | `file_cache`, `discover_paths`, `snapshot_mtimes`, `files_changed` |

---

### Migration from v0.2.x

**Additive.** No removals. New kwargs default off (`watch_files=False`).

| Change | Action |
|---|---|
| Cache key digests | Deploy; accept misses for set/tuple/dataclass/model args |
| FastAPI default store | Pass explicit `store=` to both decorators if you relied on implicit sharing |
| HTTP cache / ETag / sliding TTL | Unchanged from v0.2.x |

Examples: `examples/sqlite/`, `examples/rag/`, `examples/files/`.

---

### Requirements

- Python 3.10+
- MIT License

### Note

**Per-process** in-memory cache. `uvicorn --workers N` → N independent caches.

`watch_files`: one `getmtime` per watched path per cache hit — ideal for prompt files; measure before using on hot HTTP routes.

Full docs: https://github.com/kineticquant/inhouse
