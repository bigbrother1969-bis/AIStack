from __future__ import annotations

from pathlib import Path


def page_file(directory: Path, page: str, lang: str, reference: str) -> Path:
    """
    Where one generated page lives in one language — ADR-0010 § 5.

    The reference language keeps each page's historical name and, with
    it, its history stream (`console.html`, `history/console/`); every
    other language sits beside it as `<stem>.<code>.html`
    (`console.en.html`, `history/console.en/`). The commands that write
    a page and the server that reads it both name the file through
    this one function, so the two can never disagree on it.
    """

    if lang == reference:
        return directory / page

    return directory / f"{page.removesuffix('.html')}.{lang}.html"
