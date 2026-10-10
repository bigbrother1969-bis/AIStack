from __future__ import annotations

from pathlib import Path


def page_file(directory: Path, page: str, lang: str, reference: str) -> Path:
    """Path of one generated page in one language (ADR-0010 § 5).

    The reference language keeps the plain name (`console.html`); other
    languages use `<stem>.<code>.html` (`console.en.html`). Writers and the
    server both call this function so they always agree on the file name.
    """

    if lang == reference:
        return directory / page

    return directory / f"{page.removesuffix('.html')}.{lang}.html"
