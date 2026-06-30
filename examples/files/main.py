"""File-backed prompt caching recipe for inhouse-cache v0.3.0."""

from __future__ import annotations

import os
from pathlib import Path

from inhouse.files import file_cache

PROMPT_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT = PROMPT_DIR / "system.md"


@file_cache(3600, watch_files=["*.md"])
def load_prompt_from_path(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


@file_cache(3600, watch_files=[str(SYSTEM_PROMPT)])
def load_static_system_prompt() -> str:
    return SYSTEM_PROMPT.read_text(encoding="utf-8")


if __name__ == "__main__":
    if os.environ.get("INHOUSE_CACHE_DISABLE"):
        from inhouse import disable_all

        disable_all()

    PROMPT_DIR.mkdir(exist_ok=True)
    SYSTEM_PROMPT.write_text("# System\nYou are helpful.", encoding="utf-8")
    assert "helpful" in load_prompt_from_path(str(SYSTEM_PROMPT))
    assert "helpful" in load_static_system_prompt()
