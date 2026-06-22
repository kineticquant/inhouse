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
