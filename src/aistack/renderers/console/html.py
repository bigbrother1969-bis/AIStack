from __future__ import annotations

from aistack.contracts.console_link import ConsoleLink
from aistack.renderers.console.assets import LOCKUP_DATA_URI, MARK_DATA_URI
from aistack.renderers.text import escape_text


def render_html(links: tuple[ConsoleLink, ...]) -> str:
    """
    Wrap the owner's declared `ConsoleLink`s into one self-contained
    HTML page — `PLAN-J11`'s console
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` § 2), the third tenant of
    the `renderers/` package after `aistack.renderers.architecture`
    and `aistack.renderers.health`.

    **A landing page, not a fifth domain.** Unlike `health.html`,
    there is no finding to qualify and no absence to name honestly —
    every link here is a routing decision the owner already made
    (`ConsoleLink.__post_init__` only checks it is well-formed, never
    whether the target is actually reachable right now — this
    renderer has no provider of its own and reaches out to nothing,
    the same "render what it's handed" discipline every renderer in
    this package already holds).

    **The lockup and the mark carry the branding, not this
    function.** The embedded lockup
    (`aistack.renderers.console.assets.LOCKUP_DATA_URI`) is the header
    banner, the mark (`MARK_DATA_URI`) is the favicon — both the
    owner's own charte graphique, vendored inline: no CDN, no external
    network access, matching `architecture.html`'s mermaid.js and
    `health.html`'s script-free page alike, so this page renders
    correctly with no outbound internet, the normal state of the LAN
    it lives on.

    Pure — no wall clock: the same links always render to
    byte-identical output, so `ConsoleHtmlArtifactGenerator`
    (`aistack/generators/console/html_artifact.py`) is what stamps
    *when* a copy was produced, via `write_artifact_with_history`, not
    this function.
    """

    cards = "\n".join(_render_link(link) for link in links)

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>AIStack — Console</title>
<link rel="icon" href="{MARK_DATA_URI}">
<style>
{_STYLE}
</style>
</head>
<body>
<header>
  <img class="lockup" src="{LOCKUP_DATA_URI}" alt="AIStack — Infrastructure Knowledge Platform">
</header>

<main class="links">
{cards}
</main>
</body>
</html>
"""


def _render_link(link: ConsoleLink) -> str:
    return f"""  <a class="card" href="{escape_text(link.url)}">
    <h2>{escape_text(link.name)}</h2>
    <p>{escape_text(link.description)}</p>
    <span class="url">{escape_text(link.url)}</span>
  </a>"""


_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: sans-serif; max-width: 900px; margin: 2rem auto;
  color: #1f2933; padding: 0 1rem;
}
header { text-align: center; margin-bottom: 2rem; }
.lockup { max-width: 340px; width: 100%; height: auto; }
.links {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}
.card {
  display: block; border: 1px solid #ddd; border-radius: 8px;
  padding: 1rem 1.2rem; text-decoration: none; color: inherit;
  background: #fafcff; transition: border-color .15s ease;
}
.card:hover { border-color: #1f6feb; }
.card h2 { margin: 0 0 .4rem; font-size: 1.05rem; color: #0b3d91; }
.card p { margin: 0 0 .6rem; font-size: .9rem; color: #444; }
.card .url { font-size: .78rem; color: #888; font-family: monospace; }\
"""
