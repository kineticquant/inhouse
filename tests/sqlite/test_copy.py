from __future__ import annotations

import sqlite3

from inhouse.sqlite import query_store, rows_to_dicts, safe_copy


def test_safe_copy_handles_sqlite_row() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    connection.execute("INSERT INTO users VALUES (1, 'ada')")
    row = connection.execute("SELECT * FROM users").fetchone()

    copied = safe_copy(row)
    assert copied == {"id": 1, "name": "ada"}
    copied["name"] = "changed"
    assert dict(row)["name"] == "ada"


def test_rows_to_dicts_converts_sequences() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE users (id INTEGER)")
    connection.execute("INSERT INTO users VALUES (1), (2)")
    rows = connection.execute("SELECT * FROM users").fetchall()

    converted = rows_to_dicts(rows)
    assert converted == [{"id": 1}, {"id": 2}]


def test_query_store_uses_safe_copy_on_read() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE users (id INTEGER)")
    connection.execute("INSERT INTO users VALUES (1)")
    row = connection.execute("SELECT * FROM users").fetchone()

    store = query_store(default_ttl=60)
    store.set("key", row, 60)
    value = store.get("key")
    assert value == {"id": 1}
    value["id"] = 99
    assert store.get("key") == {"id": 1}
