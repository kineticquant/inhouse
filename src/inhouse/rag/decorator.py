from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from inhouse.decorator import cache

F = TypeVar("F", bound=Callable[..., Any])


def rag_cache(
    ttl_seconds: float | Callable[[], float] | None = 600,
    **kwargs: Any,
) -> Callable[[F], F]:
    return cache(ttl_seconds, **kwargs)
