from __future__ import annotations

from typing import Any

from inhouse.sqlite.copy import safe_copy
from inhouse.store import MemoryStore


def query_store(**kwargs: Any) -> MemoryStore:
    return MemoryStore(copy_on_read=True, copy_fn=safe_copy, **kwargs)
