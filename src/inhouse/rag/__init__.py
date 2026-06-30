"""RAG prompt caching presets."""

__all__ = ["rag_cache"]


def __getattr__(name: str) -> object:
    if name == "rag_cache":
        from inhouse.rag.decorator import rag_cache

        return rag_cache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
