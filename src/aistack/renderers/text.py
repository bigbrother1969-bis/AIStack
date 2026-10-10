from __future__ import annotations

import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def escape_text(text: str) -> str:
    """Escape text for an HTML attribute or body, or a Mermaid label.

    Apply it to interpolated parts only, never to markup the caller writes
    itself (`<br/>`, `<small>`), or that markup shows as text.
    """

    return (
        text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def domain_slug(name: str) -> str:
    """URL-anchor-safe id for a `HealthDomain.name` ("Tests PRA" -> "tests-pra").

    Accented characters are dropped, not transliterated. `console.html` uses it
    to link to the matching `<section id="domain-<slug>">` in `health.html`.
    """

    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "domain"
