from __future__ import annotations

from pathlib import Path

from inhouse import disable_all, enable_all
from inhouse.files import file_cache


def test_file_cache_recomputes_when_watched_file_changes(tmp_path: Path) -> None:
    prompt = tmp_path / "skill.md"
    prompt.write_text("v1", encoding="utf-8")
    calls = {"count": 0}

    @file_cache(60, watch_files=["*.md"])
    def load_prompt(path: str) -> str:
        calls["count"] += 1
        return path + ":" + prompt.read_text(encoding="utf-8")

    path = str(prompt)
    first = load_prompt(path)
    second = load_prompt(path)
    assert first == second
    assert calls["count"] == 1

    prompt.write_text("v2", encoding="utf-8")
    third = load_prompt(path)
    assert third.endswith(":v2")
    assert calls["count"] == 2


def test_file_cache_respects_disable_all(tmp_path: Path) -> None:
    prompt = tmp_path / "skill.md"
    prompt.write_text("v1", encoding="utf-8")
    calls = {"count": 0}

    @file_cache(60, watch_files=True)
    def load_prompt(path: str) -> str:
        calls["count"] += 1
        return prompt.read_text(encoding="utf-8")

    path = str(prompt)
    assert load_prompt(path) == "v1"
    disable_all()
    assert load_prompt(path) == "v1"
    assert calls["count"] == 2
    enable_all()
