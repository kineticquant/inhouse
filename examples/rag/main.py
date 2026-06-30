"""RAG prompt compilation caching recipe for inhouse-cache v0.3.0."""

from __future__ import annotations

import asyncio

from inhouse import MemoryStore
from inhouse.rag import rag_cache

store = MemoryStore(default_ttl=600)


@rag_cache(store=store)
async def compile_rag_prompt(user_query: str, filters: dict[str, object], corpus_version: str) -> str:
    # 1. expensive vector search would run here on cache miss
    context = f"docs matching {filters!r}"
    # 2. render prompt template
    return f"Context: {context}\nCorpus: {corpus_version}\n\nQuestion: {user_query}"


async def ingest_documents(new_version: str) -> None:
    # after ingestion, bump corpus_version or clear the cache explicitly
    compile_rag_prompt.cache_clear()
    _ = new_version


async def main() -> None:
    first = await compile_rag_prompt("hello", {"tags": {"ai", "cache"}}, "v1")
    second = await compile_rag_prompt("hello", {"tags": {"cache", "ai"}}, "v1")
    assert first == second
    await ingest_documents("v2")
    third = await compile_rag_prompt("hello", {"tags": {"ai"}}, "v2")
    assert "v2" in third


if __name__ == "__main__":
    asyncio.run(main())
