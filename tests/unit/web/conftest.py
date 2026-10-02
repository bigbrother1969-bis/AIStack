from __future__ import annotations

from pathlib import Path

import pytest

from aistack.console.routing import PAGES


@pytest.fixture
def generated(tmp_path: Path) -> Path:
    """The three console pages in both languages, plus a file never served."""

    for page in PAGES:
        stem = page.removesuffix(".html")
        (tmp_path / page).write_text(f"<p>{stem} fr</p>", encoding="utf-8")
        (tmp_path / f"{stem}.en.html").write_text(f"<p>{stem} en</p>", encoding="utf-8")

    (tmp_path / "docker-observation.json").write_text("{}", encoding="utf-8")

    return tmp_path
