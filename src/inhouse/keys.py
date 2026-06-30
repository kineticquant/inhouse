from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any


def freeze_for_key(value: Any) -> Any:
    # recursive freeze for stable cache keys
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return tuple(
            (str(k), freeze_for_key(v))
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        )
    if isinstance(value, list):
        return ("__list__", tuple(freeze_for_key(item) for item in value))
    if isinstance(value, tuple):
        return ("__tuple__", tuple(freeze_for_key(item) for item in value))
    if isinstance(value, set | frozenset):
        return frozenset(freeze_for_key(item) for item in value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        qualname = f"{type(value).__module__}.{type(value).__qualname__}"
        fields = dataclasses.fields(value)
        return (
            "dataclass",
            qualname,
            tuple(freeze_for_key(getattr(value, field.name)) for field in fields),
        )
    # pydantic duck-type without importing pydantic
    model_fields = getattr(type(value), "model_fields", None)
    if model_fields is not None:
        qualname = f"{type(value).__module__}.{type(value).__qualname__}"
        dumped = value.model_dump() if hasattr(value, "model_dump") else dict(value)
        return ("pydantic", qualname, freeze_for_key(dumped))
    legacy_fields = getattr(type(value), "__fields__", None)
    if legacy_fields is not None:
        qualname = f"{type(value).__module__}.{type(value).__qualname__}"
        dumped = value.dict() if hasattr(value, "dict") else dict(value)
        return ("pydantic", qualname, freeze_for_key(dumped))
    return f"{type(value).__module__}.{type(value).__qualname__}:{value!s}"


def _to_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, tuple):
        if value and value[0] in ("dataclass", "pydantic", "__list__", "__tuple__"):
            return [_to_json_safe(item) for item in value]
        return ["__tuple__", *[_to_json_safe(item) for item in value]]
    if isinstance(value, frozenset):
        parts = sorted(
            (_to_json_safe(item) for item in value),
            key=lambda item: json.dumps(item, sort_keys=True),
        )
        return ["__frozenset__", *parts]
    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {
            str(k): _to_json_safe(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    return value


def _normalize_value(value: Any) -> Any:
    return _to_json_safe(freeze_for_key(value))


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


# stable sha-256 hex digest for a cached response value (canonical json)
def stable_value_digest(value: Any) -> str:
    normalized = _normalize_value(value)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# weak http etag header value for a cached response body
def make_weak_etag(value: Any) -> str:
    return f'W/"{stable_value_digest(value)}"'


# deterministic cache key from function identity and call arguments
def make_cache_key(func: Callable[..., Any], args: Sequence[Any], kwargs: Mapping[str, Any], *, exclude_types: tuple[type[Any], ...] = ()) -> str:  # noqa: E501
    material = _collect_key_material(args, kwargs, exclude_types)
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{func.__module__}.{func.__qualname__}:{digest}"
