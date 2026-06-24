from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from inhouse.fastapi import create_lifespan, fastapi_cache
from inhouse.keys import make_weak_etag
from inhouse.store import MemoryStore


def _app(store: MemoryStore | None = None) -> tuple[FastAPI, MemoryStore]:
    target = store or MemoryStore()
    return FastAPI(lifespan=create_lifespan(target, sweep_interval=3600.0)), target


# cache hit emits private cache-control with positive max-age and coalesces handler calls
@pytest.mark.asyncio
async def test_private_max_age() -> None:
    app, store = _app()
    calls = {"count": 0}

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, http_cache=True)
    async def get_item(item_id: int) -> dict[str, int]:
        calls["count"] += 1
        return {"item_id": item_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/items/1")
        second = await client.get("/items/1")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["count"] == 1
    assert second.headers["cache-control"].startswith("private, max-age=")
    assert int(second.headers["cache-control"].split("max-age=")[1]) > 0


# cache-control visibility is public when cache_visibility="public"
@pytest.mark.asyncio
async def test_public_max_age() -> None:
    app, store = _app()

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, http_cache=True, cache_visibility="public")
    async def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/items/1")

    assert response.headers["cache-control"].startswith("public, max-age=")


# no cache-control or etag headers when http_cache and etag are disabled
@pytest.mark.asyncio
async def test_no_headers_by_default() -> None:
    app, store = _app()

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store)
    async def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/items/1")

    assert "cache-control" not in response.headers
    assert "etag" not in response.headers


# etag on 200; matching if-none-match yields 304 with empty body
@pytest.mark.asyncio
async def test_etag_304_on_hit() -> None:
    app, store = _app()
    calls = {"count": 0}
    body = {"item_id": 1}
    etag = make_weak_etag(body)

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, etag=True)
    async def get_item(item_id: int) -> dict[str, int]:
        calls["count"] += 1
        return body

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/items/1")
        second = await client.get("/items/1", headers={"If-None-Match": etag})

    assert first.status_code == 200
    assert first.headers["etag"] == etag
    assert second.status_code == 304
    assert second.content == b""
    assert calls["count"] == 1


# cold miss still returns 304 when if-none-match matches freshly computed etag
@pytest.mark.asyncio
async def test_etag_304_on_miss() -> None:
    app, store = _app()
    body = {"item_id": 1}
    etag = make_weak_etag(body)

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, etag=True)
    async def get_item(item_id: int) -> dict[str, int]:
        return body

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/items/1", headers={"If-None-Match": etag})

    assert response.status_code == 304
    assert store.size == 1


# http_cache + etag together: both headers on 200, 304 on match
@pytest.mark.asyncio
async def test_combined_headers() -> None:
    app, store = _app()
    body = {"item_id": 1}
    etag = make_weak_etag(body)

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, http_cache=True, etag=True, cache_visibility="public")
    async def get_item(item_id: int) -> dict[str, int]:
        return body

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/items/1")
        second = await client.get("/items/1", headers={"If-None-Match": etag})

    assert first.headers["cache-control"].startswith("public, max-age=")
    assert first.headers["etag"] == etag
    assert second.status_code == 304
    assert second.headers["etag"] == etag
    assert "cache-control" in second.headers


# sliding ttl extends max-age on a subsequent cache hit
@pytest.mark.asyncio
async def test_sliding_max_age() -> None:
    app, store = _app()
    base = 1000.0
    clock = {"now": base}

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, sliding=True, http_cache=True)
    async def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    transport = ASGITransport(app=app)
    with patch("inhouse.store.time.monotonic", lambda: clock["now"]):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/items/1")
            clock["now"] = base + 50
            second = await client.get("/items/1")

    max_age = int(second.headers["cache-control"].split("max-age=")[1])
    assert max_age >= 59
