"""SQLite query caching recipe for inhouse-cache v0.3.0."""

from __future__ import annotations

import sqlite3
import threading

from inhouse import inhouse_cache
from inhouse.sqlite import query_store, rows_to_dicts

_store = query_store(max_size=1024, default_ttl=60)
_local = threading.local()


def get_connection() -> sqlite3.Connection:
    # ponytail: thread-local connection; keep db handles out of cache keys
    connection = getattr(_local, "connection", None)
    if connection is None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE settings (user_id INTEGER, theme TEXT)")
        connection.execute("INSERT INTO settings VALUES (1, 'dark')")
        _local.connection = connection
    return connection


@inhouse_cache(store=_store)
def fetch_user_settings(user_id: int) -> dict[str, object] | None:
    connection = get_connection()
    row = connection.execute("SELECT * FROM settings WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    # advanced path: map to dict/dataclass before return for hot paths
    return rows_to_dicts(row)


if __name__ == "__main__":
    assert fetch_user_settings(1) == {"user_id": 1, "theme": "dark"}
    assert fetch_user_settings(1) == {"user_id": 1, "theme": "dark"}
