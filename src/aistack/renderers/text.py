from __future__ import annotations


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
