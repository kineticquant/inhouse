from __future__ import annotations

import asyncio

from fastapi import FastAPI

from inhouse import MemoryStore
from inhouse.fastapi import create_lifespan, fastapi_cache

store = MemoryStore(max_size=256)
app = FastAPI(lifespan=create_lifespan(store, sweep_interval=30.0))


@app.get("/items/{item_id}")
@fastapi_cache(60, store=store)
async def get_item(item_id: int) -> dict[str, int | str]:
    await asyncio.sleep(0.1)
    return {"item_id": item_id, "source": "database"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
