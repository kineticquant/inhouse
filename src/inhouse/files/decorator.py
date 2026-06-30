from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from inhouse.decorator import cache

F = TypeVar("F", bound=Callable[..., Any])


def file_cache(
    ttl_seconds: float | Callable[[], float] | None = 3600,
    *,
    watch_files: bool | list[str] = True,
    **kwargs: Any,
) -> Callable[[F], F]:
    return cache(ttl_seconds, watch_files=watch_files, **kwargs)
