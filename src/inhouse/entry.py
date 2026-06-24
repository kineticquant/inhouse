from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CacheEntry:
    expires_at: float
    value: Any
    ttl_seconds: float
    sliding: bool = False
    etag: str | None = None
