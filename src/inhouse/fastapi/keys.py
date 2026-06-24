from __future__ import annotations

from typing import Any

from inhouse.keys import make_cache_key

try:
    from starlette.requests import Request
    from starlette.responses import Response

    _FASTAPI_EXCLUDE_TYPES: tuple[type[Any], ...] = (Request, Response)
except ImportError:  # pragma: no cover - optional dependency
    _FASTAPI_EXCLUDE_TYPES = ()


def make_fastapi_cache_key(
    func: Any,
    args: Any,
    kwargs: Any,
    *,
    exclude_types: tuple[type[Any], ...] = (),
) -> str:
    merged_exclude = _FASTAPI_EXCLUDE_TYPES + exclude_types
    return make_cache_key(func, args, kwargs, exclude_types=merged_exclude)
