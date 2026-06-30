from __future__ import annotations

import os
from pathlib import Path

from inhouse.files.watch import discover_paths, files_changed, snapshot_mtimes


def test_discover_paths_from_arguments(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("hello", encoding="utf-8")

    paths = discover_paths((str(prompt),), {}, True)
    assert paths == [os.path.abspath(prompt)]


def test_discover_paths_with_glob_filter(tmp_path: Path) -> None:
    markdown = tmp_path / "skill.md"
    text = tmp_path / "notes.txt"
    markdown.write_text("md", encoding="utf-8")
    text.write_text("txt", encoding="utf-8")

    paths = discover_paths((str(markdown), str(text)), {}, ["*.md"])
    assert paths == [os.path.abspath(markdown)]


def test_discover_paths_with_explicit_static_path(tmp_path: Path) -> None:
    static = tmp_path / "static.md"
    static.write_text("static", encoding="utf-8")

    paths = discover_paths((), {}, [str(static)])
    assert paths == [os.path.abspath(static)]


def test_files_changed_detects_mtime_updates(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("v1", encoding="utf-8")
    path = os.path.abspath(prompt)
    stored = snapshot_mtimes([path])

    assert files_changed(stored, [path]) is False

    os.utime(path, (stored[path] + 5, stored[path] + 5))
    assert files_changed(stored, [path]) is True
