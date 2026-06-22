from __future__ import annotations

import asyncio

import pytest

from inhouse.decorator import cache
from inhouse.store import MemoryStore


@pytest.mark.asyncio
async def test_async_decorator_caches_result() -> None:
    store = MemoryStore()
    calls = {"count": 0}

    @cache(60, store=store)
    async def compute(value: int) -> int:
        calls["count"] += 1
        await asyncio.sleep(0)
        return value * 2

    assert await compute(2) == 4
    assert await compute(2) == 4
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_async_decorator_respects_ttl() -> None:
    store = MemoryStore()
    calls = {"count": 0}

    @cache(0.01, store=store)
    async def compute() -> int:
        calls["count"] += 1
        return calls["count"]

    first = await compute()
    second = await compute()
    assert first == second == 1

    await asyncio.sleep(0.02)
    third = await compute()
    assert third == 2
    assert calls["count"] == 2
