"""File-backed cache helpers (mtime watching, prompt presets)."""

from inhouse.files.watch import discover_paths, files_changed, snapshot_mtimes

__all__ = ["discover_paths", "file_cache", "files_changed", "snapshot_mtimes"]


def __getattr__(name: str) -> object:
    if name == "file_cache":
        from inhouse.files.decorator import file_cache

        return file_cache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
