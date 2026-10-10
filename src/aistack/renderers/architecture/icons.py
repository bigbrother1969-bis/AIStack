from __future__ import annotations

import base64
from pathlib import Path

_ICONS_DIR = Path(__file__).resolve().parent / "vendor" / "icons"

# Suffixes tried in order; `vendor/icons/PROVENANCE.md` lists each icon's source.
_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


def load_icon_data_uri(icon_key: str | None) -> str | None:
    """Resolve an icon key to an embeddable `data:` URI, or `None`.

    `None` covers both a missing key and a key with no vendored file, so a
    typo loses one icon instead of breaking the render. Icons are read from
    disk because `architecture.html` works without network access.
    """

    if not icon_key:
        return None

    for suffix, mime in _MIME_BY_SUFFIX.items():
        path = _ICONS_DIR / f"{icon_key}{suffix}"

        if path.is_file():
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{encoded}"

    return None
