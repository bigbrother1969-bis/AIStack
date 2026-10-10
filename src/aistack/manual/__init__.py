"""The user manual: one Markdown source per language, `manual.<code>.md`.

A language without its own manual falls back to the reference language.
"""

from __future__ import annotations

from pathlib import Path

MANUAL_DIR = Path(__file__).resolve().parent


def manual_source(lang: str, reference: str = "fr") -> str:
    path = MANUAL_DIR / f"manual.{lang}.md"
    if not path.exists():
        path = MANUAL_DIR / f"manual.{reference}.md"
    return path.read_text(encoding="utf-8")
