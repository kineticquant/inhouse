from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from inhouse.fastapi import create_lifespan, fastapi_cache
from inhouse.store import MemoryStore


@pytest.mark.asyncio
async def test_fastapi_route_cache_stampede() -> None:
    store = MemoryStore()
    calls = {"count": 0}
    counter_lock = asyncio.Lock()

    app = FastAPI(lifespan=create_lifespan(store, sweep_interval=3600.0))

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store)
    async def get_item(item_id: int) -> dict[str, int]:
        async with counter_lock:
            calls["count"] += 1
        await asyncio.sleep(0.05)
        return {"item_id": item_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        responses = await asyncio.gather(*[client.get("/items/1") for _ in range(50)])

    assert all(response.status_code == 200 for response in responses)
    assert all(response.json() == {"item_id": 1} for response in responses)
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_fastapi_cache_custom_key_builder() -> None:
    store = MemoryStore()
    calls = {"count": 0}

    def custom_key_builder(
        func: object,
        args: object,
        kwargs: object,
        *,
        exclude_types: tuple[type[object], ...] = (),
    ) -> str:
        return "fixed-key"

    app = FastAPI(lifespan=create_lifespan(store, sweep_interval=3600.0))

    @app.get("/items/{item_id}")
    @fastapi_cache(60, store=store, key_builder=custom_key_builder)
    async def get_item(item_id: int) -> dict[str, int]:
        calls["count"] += 1
        return {"item_id": item_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/items/1")
        second = await client.get("/items/2")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == {"item_id": 1}
    assert second.json() == {"item_id": 1}
    assert calls["count"] == 1
