from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from inhouse.fastapi import create_lifespan, fastapi_cache
from inhouse.store import MemoryStore


def _app(store: MemoryStore | None = None) -> tuple[FastAPI, MemoryStore]:
    target = store or MemoryStore()
    return FastAPI(lifespan=create_lifespan(target, sweep_interval=3600.0)), target


# per-client request headers must not bust cache keys or force extra handler runs
@pytest.mark.asyncio
async def test_cache_key_ignores_client_headers() -> None:
    app, store = _app()
    calls = {"count": 0}

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, http_cache=True)
    async def get_item(item_id: int) -> dict[str, int]:
        calls["count"] += 1
        return {"item_id": item_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/items/1", headers={"X-Client": "a"})
        await client.get("/items/1", headers={"X-Client": "b"})

    assert calls["count"] == 1


# declared request: Request on the handler must still be forwarded when present
@pytest.mark.asyncio
async def test_declared_request_forwarded() -> None:
    app, store = _app()

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, etag=True)
    async def get_item(item_id: int, request: Request) -> dict[str, int | str]:
        return {"item_id": item_id, "method": request.method}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/items/1")

    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "method": "GET"}


# spoofed if-none-match must not yield 304 when etag does not match stored value
@pytest.mark.asyncio
async def test_spoofed_etag_no_304() -> None:
    app, store = _app()
    body = {"item_id": 1}

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, etag=True)
    async def get_item(item_id: int) -> dict[str, int]:
        return body

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/items/1")
        response = await client.get("/items/1", headers={"If-None-Match": 'W/"not-the-real-etag"'})

    assert response.status_code == 200
    assert response.json() == body
