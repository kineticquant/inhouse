from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(k): _normalize_value(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list | tuple):
        return [_normalize_value(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _collect_key_material(
    args: Sequence[Any],
    kwargs: Mapping[str, Any],
    exclude_types: tuple[type[Any], ...],
) -> dict[str, Any]:
    filtered_args = [arg for arg in args if not isinstance(arg, exclude_types)]
    filtered_kwargs = {
        key: value for key, value in sorted(kwargs.items()) if not isinstance(value, exclude_types)
    }
    return {
        "args": [_normalize_value(arg) for arg in filtered_args],
        "kwargs": {key: _normalize_value(value) for key, value in filtered_kwargs.items()},
    }


def make_cache_key(
    func: Callable[..., Any],
    args: Sequence[Any],
    kwargs: Mapping[str, Any],
    *,
    exclude_types: tuple[type[Any], ...] = (),
) -> str:
    """Build a deterministic cache key from function identity and call arguments."""
    material = _collect_key_material(args, kwargs, exclude_types)
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{func.__module__}.{func.__qualname__}:{digest}"
