from __future__ import annotations

import asyncio

import pytest

from inhouse.decorator import cache
from inhouse.store import MemoryStore


@pytest.mark.asyncio
async def test_decorator_uses_store_default_ttl() -> None:
    store = MemoryStore(default_ttl=60)
    calls = {"count": 0}

    @cache(store=store)
    async def compute(value: int) -> int:
        calls["count"] += 1
        return value

    assert await compute(1) == 1
    assert await compute(1) == 1
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_decorator_uses_callable_ttl() -> None:
    store = MemoryStore()
    ttl = {"seconds": 60}

    @cache(lambda: ttl["seconds"], store=store)
    async def compute() -> str:
        return "ok"

    assert await compute() == "ok"

    ttl["seconds"] = 0.01
    await asyncio.sleep(0.02)
    assert await compute() == "ok"
