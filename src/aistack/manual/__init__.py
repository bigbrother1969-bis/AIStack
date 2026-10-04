"""
The user manual (asked by the owner, 2026-10-04): one Markdown source
per declared language, `manual.<code>.md`, rendered to a page the
console's Help leads to. The reference language's text is the fallback
for a language that has none yet.
"""

from __future__ import annotations

from pathlib import Path

MANUAL_DIR = Path(__file__).resolve().parent


def manual_source(lang: str, reference: str = "fr") -> str:
    path = MANUAL_DIR / f"manual.{lang}.md"
    if not path.exists():
        path = MANUAL_DIR / f"manual.{reference}.md"
    return path.read_text(encoding="utf-8")
