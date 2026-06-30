from __future__ import annotations

import copy
import sqlite3
from typing import Any


def _is_sqlite_row(value: Any) -> bool:
    return isinstance(value, sqlite3.Row)


def rows_to_dicts(rows: Any) -> Any:
    if _is_sqlite_row(rows):
        return dict(rows)
    if isinstance(rows, list):
        return [rows_to_dicts(row) for row in rows]
    if isinstance(rows, tuple):
        return tuple(rows_to_dicts(row) for row in rows)
    return rows


def safe_copy(value: Any) -> Any:
    try:
        return copy.deepcopy(value)
    except TypeError:
        if _is_sqlite_row(value):
            return copy.deepcopy(dict(value))
        if isinstance(value, list):
            return [safe_copy(item) for item in value]
        if isinstance(value, tuple):
            return tuple(safe_copy(item) for item in value)
        raise
