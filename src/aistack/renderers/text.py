from __future__ import annotations

import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def escape_text(text: str) -> str:
    """
    Escape one piece of declared text for use inside an HTML
    attribute or element body, or a Mermaid node/subgraph label — the
    same four characters are unsafe in both contexts, and this
    heritage has one escaping function rather than two that could
    drift apart.

    **Moved here from `aistack.renderers.architecture.mermaid`,
    2026-09-11**, when `aistack.renderers.health.html` became this
    function's second caller — that module's own docstring already
    named the reasoning ("one escaping function... rather than two"),
    so a second, HTML-only renderer duplicating the same four
    `.replace()` calls would have been the exact drift that reasoning
    was written to avoid. `aistack.renderers.architecture.mermaid`
    still exposes `escape_text` at its own module level, re-exported
    from here, so nothing that already imported it from there needed
    to change.

    Applied to the *interpolated* parts of a label only, never to
    literal markup a caller writes itself (`<br/>`, `<small>`) —
    escaping those too would print them as visible text instead of
    rendering them.
    """

    return (
        text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def domain_slug(name: str) -> str:
    """
    A stable, URL-anchor-safe id for a `HealthDomain.name` — "Tests
    PRA" -> "tests-pra". An accented character is dropped, not
    transliterated, the same trade-off
    `aistack.renderers.architecture.mermaid._slug` already makes for
    its own Mermaid node ids (that function keeps its own private
    `_slug`, with underscores rather than this function's hyphens —
    a Mermaid node id and an HTML anchor id are different enough
    targets that sharing one helper would tie them together for no
    real benefit; only the small regex idea is the same).

    Every domain name `aistack.cli.health_render.build_cockpit`
    assembles (Stockage, Services, Sauvegarde / PRA, GPU, Tests PRA,
    État persistant, Écarts d'inventaire) stays unique after slugging
    — checked directly in `tests/unit/renderers/test_text.py`, not
    just assumed.

    **Added 2026-09-30** so `console.html`'s own domain pills
    (`aistack.renderers.console.html`) can link to `health.html`'s
    matching `<section id="domain-<slug>">`
    (`aistack.renderers.health.html`) — the two renderers never share
    code, only this one small transform, the same "one shared
    function rather than two that could drift" reasoning
    `escape_text` itself already holds in this module.
    """

    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "domain"
