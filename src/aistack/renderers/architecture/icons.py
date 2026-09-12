from __future__ import annotations

import base64
from pathlib import Path

_ICONS_DIR = Path(__file__).resolve().parent / "vendor" / "icons"

# Checked in this order for a given key: most services in
# `service_categorization.yml` declare a dashboard-icons PNG, a
# minority declare a Material Design Icons or Font Awesome SVG —
# `vendor/icons/PROVENANCE.md` names exactly which. Neither this
# module nor its caller needs to know which one a given key is; it
# tries the one convention this vendor directory actually uses (a
# bare slug, no source-specific prefix) against both extensions.
_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


def load_icon_data_uri(icon_key: str | None) -> str | None:
    """
    Resolve a declared icon key to an embeddable `data:` URI, or
    `None` if the key is absent or names no vendored file.

    **`None` on a miss, not a raised error.** A service the owner
    declares with no `icon:` at all (`ServiceDefinition.icon is None`)
    is normal, not a defect — this mirrors `container: None` already
    meaning "nothing to look up" one call away in `graph.py`. A
    non-`None` key naming no vendored file (a typo, an icon removed
    from `vendor/icons/` without updating the categorization) is
    treated the same way rather than crashing the whole render: an
    architecture diagram missing one icon is still useful; one that
    refuses to render at all because of it is not.

    **Read from disk beside this module**, the same
    `Path(__file__).resolve()`-relative convention
    `load_vendored_mermaid_js` already uses one directory over —
    `architecture.html` renders with no network access at all, so
    every icon it shows has to already be a file in this repository.
    """

    if not icon_key:
        return None

    for suffix, mime in _MIME_BY_SUFFIX.items():
        path = _ICONS_DIR / f"{icon_key}{suffix}"

        if path.is_file():
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{encoded}"

    return None
