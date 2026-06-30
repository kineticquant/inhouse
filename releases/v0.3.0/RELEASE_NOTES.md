# Release Notes

## inhouse-cache v0.3.0

**Phase 4:** vertical caching patterns for SQLite queries, RAG prompt compilation, and file-backed AI prompts — plus core decorator enhancements.

Zero-dependency core. Optional FastAPI extra unchanged for users who already use it.

### Install

```bash
pip install inhouse-cache
```

Vertical helpers ship in the default wheel (no `[sqlite]` / `[rag]` / `[files]` extras):

```python
from inhouse.sqlite import query_store
from inhouse.rag import rag_cache
from inhouse.files import file_cache
```

### Key Release Highlights

1. **Recursive key freezing** — stable cache keys for sets, nested mappings, dataclasses, and Pydantic-like models (`freeze_for_key` / updated `make_cache_key`).

2. **`cache_clear()`** — decorated functions expose `func.cache_clear()` to purge that function's cache entries (`MemoryStore.delete_prefix`).

3. **`disable_all()` / `INHOUSE_CACHE_DISABLE`** — global dev bypass; all decorators call through without caching.

4. **`watch_files`** — lazy `mtime` invalidation for file-backed cached content (`True`, globs like `["*.md"]`, or explicit paths).

5. **FastAPI store isolation** — `@fastapi_cache` uses `get_fastapi_default_store()` by default, separate from core `get_default_store()`.

6. **Vertical packages** (always installed):
   - `inhouse.sqlite` — `query_store()`, `safe_copy()`, `rows_to_dicts()` for SQLite `Row` mutate protection
   - `inhouse.rag` — `rag_cache()` preset for prompt compilation
   - `inhouse.files` — `file_cache()` preset + watch helpers

7. **`MemoryStore(copy_fn=...)`** — plug custom copy logic when `copy_on_read=True`.

### Breaking changes

Cache key semantics changed for some argument types (sets, list vs tuple, dataclass/Pydantic-like inputs). Expect cache misses after upgrade — not data corruption.

### Migration from v0.2.x

- No API removals.
- New optional decorator kwargs default to off (`watch_files=False`, etc.).
- Pass the same `MemoryStore` to core and FastAPI decorators if you want a shared memory budget (default is now isolated).
- Examples: `examples/sqlite/`, `examples/rag/`, `examples/files/`.

### Requirements

- Python 3.10+
- MIT License
