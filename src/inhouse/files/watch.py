from __future__ import annotations

import fnmatch
import os
from collections.abc import Mapping, Sequence
from typing import Any


def _walk_values(value: Any) -> list[Any]:
    if isinstance(value, Mapping):
        return [item for mapping_value in value.values() for item in _walk_values(mapping_value)]
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [item for sequence_value in value for item in _walk_values(sequence_value)]
    return [value]


def _is_glob_pattern(pattern: str) -> bool:
    return any(char in pattern for char in "*?[]")


def discover_paths(
    args: Sequence[Any],
    kwargs: Mapping[str, Any],
    watch_files: bool | list[str],
) -> list[str]:
    if not watch_files:
        return []

    explicit_paths: list[str] = []
    glob_patterns: list[str] = []
    if isinstance(watch_files, list):
        for item in watch_files:
            if _is_glob_pattern(item):
                glob_patterns.append(item)
            elif os.path.isfile(item):
                explicit_paths.append(os.path.abspath(item))

    discovered: list[str] = []
    if watch_files is True or glob_patterns:
        for value in _walk_values((*args, *kwargs.values())):
            if not isinstance(value, str) or not os.path.isfile(value):
                continue
            path = os.path.abspath(value)
            if watch_files is True:
                discovered.append(path)
            elif any(fnmatch.fnmatch(os.path.basename(path), pattern) for pattern in glob_patterns):
                discovered.append(path)

    return sorted(set(explicit_paths + discovered))


def snapshot_mtimes(paths: Sequence[str]) -> dict[str, float]:
    return {path: os.path.getmtime(path) for path in paths}


def files_changed(stored: dict[str, float] | None, paths: Sequence[str]) -> bool:
    if not paths:
        return False
    if not stored:
        return True
    current = snapshot_mtimes(paths)
    if set(current) != set(stored):
        return True
    return any(current[path] != stored[path] for path in paths)
