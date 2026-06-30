from __future__ import annotations

import pytest

from inhouse import MemoryStore
from inhouse.rag import rag_cache


@pytest.mark.asyncio
async def test_rag_cache_presets_ttl_and_cache_clear() -> None:
    store = MemoryStore(default_ttl=60)
    calls = {"count": 0}

    @rag_cache(store=store)
    async def compile_prompt(user_query: str, corpus_version: str) -> str:
        calls["count"] += 1
        return f"{corpus_version}:{user_query}"

    first = await compile_prompt("hello", "v1")
    second = await compile_prompt("hello", "v1")
    assert first == second == "v1:hello"
    assert calls["count"] == 1

    compile_prompt.cache_clear()
    third = await compile_prompt("hello", "v1")
    assert third == "v1:hello"
    assert calls["count"] == 2


def test_rag_cache_is_alias_of_inhouse_cache() -> None:
    store = MemoryStore(default_ttl=60)

    @rag_cache(600, store=store)
    def compile_sync(query: str) -> str:
        return query

    assert hasattr(compile_sync, "cache_clear")
    assert compile_sync("x") == "x"
