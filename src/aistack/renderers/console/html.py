from __future__ import annotations

from aistack.contracts.console_link import ConsoleLink
from aistack.contracts.health_score import (
    ACTION_REQUIRED,
    EXCELLENT,
    TO_WATCH,
    HealthScore,
)
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.renderers.console.assets import LOCKUP_DATA_URI, MARK_DATA_URI
from aistack.renderers.text import escape_text

# Duplicated from `aistack.renderers.health.html._BUCKET_BADGE_CLASS`
# rather than imported: each renderer in this package is pure and
# independently testable, the same self-containment `_STYLE` already
# holds for every one of them (no shared stylesheet, no cross-renderer
# import) — a three-entry mapping is a small enough price for that.
_BUCKET_BADGE_CLASS = {
    EXCELLENT: "badge-clean",
    TO_WATCH: "badge-watch",
    ACTION_REQUIRED: "badge-alert",
}


def render_html(
    links: tuple[ConsoleLink, ...],
    cockpit: HealthCockpit | None = None,
    score: HealthScore | None = None,
    score_note: str = "",
    technical_debt_score: TechnicalDebtScore | None = None,
    technical_debt_note: str = "",
) -> str:
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

    **`cockpit`/`score`/`score_note` are optional, added
    2026-09-13** (`claude/PLAN-J11-CONSOLE-2026-09-11.md` § 11.9, the
    owner's own gap analysis against the historical `architecture.html`
    reference page's "SANTÉ HOMELAB" cartouche) — the same
    `None`-renders-exactly-as-before idiom
    `aistack.renderers.architecture.html.render_html` already holds
    for `topology`/`beszel_readings`/`dependency_graph`. `cockpit is
    None` renders the page exactly as it did before this cartouche
    existed. When a real `HealthCockpit` is handed in, this renders a
    summary banner above the link grid — the score and one badge per
    domain, reusing `aistack.health.cockpit.HealthCockpit` and
    `aistack.contracts.health_score.HealthScore` exactly as
    `aistack.renderers.health.html.render_html` already does, never a
    second scoring model invented for this page. Deliberately *not* a
    repeat of `health.html`'s own per-finding detail — this is a
    summary a viewer glances at, the full detail stays one click away
    at `/health.html`.

    **`technical_debt_score`/`technical_debt_note`, added 2026-09-23**
    (`PLAN-J11` § 11.9.1) — the same "Dette technique" card
    `aistack.renderers.health.html.render_html` shows, summarized here
    right after the global score line, the placement the owner named
    when this card was scoped ("juste après le score santé global").
    Same `None`-renders-nothing-before-this-card idiom `score`/
    `score_note` already holds.

    **The lockup and the mark carry the branding, not this
    function.** The embedded lockup
    (`aistack.renderers.console.assets.LOCKUP_DATA_URI`) is the header
    banner, the mark (`MARK_DATA_URI`) is the favicon — both the
    owner's own charte graphique, vendored inline: no CDN, no external
    network access, matching `architecture.html`'s mermaid.js and
    `health.html`'s script-free page alike, so this page renders
    correctly with no outbound internet, the normal state of the LAN
    it lives on.

    Pure — no wall clock: the same links, cockpit and score always
    render to byte-identical output, so `ConsoleHtmlArtifactGenerator`
    (`aistack/generators/console/html_artifact.py`) is what stamps
    *when* a copy was produced, via `write_artifact_with_history`, not
    this function.
    """

    cards = "\n".join(_render_link(link) for link in links)
    cartouche_html = (
        _render_health_cartouche(
            cockpit, score, score_note, technical_debt_score, technical_debt_note
        )
        if cockpit is not None
        else ""
    )

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

{cartouche_html}

<main class="links">
{cards}
</main>
</body>
</html>
"""


def _render_health_cartouche(
    cockpit: HealthCockpit,
    score: HealthScore | None,
    score_note: str,
    technical_debt_score: TechnicalDebtScore | None,
    technical_debt_note: str,
) -> str:
    if not cockpit.domains:
        return ""

    score_html = _render_cartouche_score(score, score_note)
    technical_debt_html = _render_cartouche_technical_debt(
        technical_debt_score, technical_debt_note
    )
    badges = "\n".join(_render_domain_badge(domain) for domain in cockpit.domains)

    return f"""<section class="health-cartouche">
  <div class="cartouche-header">
    <h2>État de santé du homelab</h2>
    {score_html}
  </div>
  {technical_debt_html}
  <div class="cartouche-badges">
{badges}
  </div>
  <a class="cartouche-link" href="/health.html">Voir le détail par domaine →</a>
</section>"""


def _render_cartouche_score(score: HealthScore | None, score_note: str) -> str:
    if score is not None:
        badge_class = _BUCKET_BADGE_CLASS[score.bucket]

        return (
            f'<span class="cartouche-score">Score de santé : '
            f'<strong>{score.value}/100</strong> '
            f'<span class="badge {badge_class}">{escape_text(score.bucket)}</span></span>'
        )

    if score_note:
        return (
            f'<span class="cartouche-score cartouche-score-unavailable">'
            f"Score de santé : non calculé — {escape_text(score_note)}</span>"
        )

    return ""


def _render_cartouche_technical_debt(
    score: TechnicalDebtScore | None, note: str
) -> str:
    if score is not None:
        badge_class = _BUCKET_BADGE_CLASS[score.bucket]

        return (
            f'<div class="cartouche-technical-debt">Dette technique : '
            f'<strong>{score.value}/100</strong> '
            f'<span class="badge {badge_class}">{escape_text(score.bucket)}</span></div>'
        )

    if note:
        return (
            f'<div class="cartouche-technical-debt '
            f'cartouche-technical-debt-unavailable">'
            f"Dette technique : non calculée — {escape_text(note)}</div>"
        )

    return ""


def _render_domain_badge(domain: HealthDomain) -> str:
    if not domain.instrumented:
        return (
            f'  <span class="domain-badge badge-not-instrumented">'
            f"{escape_text(domain.name)} — non instrumenté</span>"
        )

    if not domain.findings:
        return (
            f'  <span class="domain-badge badge-clean">'
            f"{escape_text(domain.name)} — rien à signaler</span>"
        )

    return (
        f'  <span class="domain-badge badge-alert">'
        f"{escape_text(domain.name)} — {len(domain.findings)} finding(s)</span>"
    )


def _render_link(link: ConsoleLink) -> str:
    """
    The card shows the name and description only — no visible URL
    text, since 2026-09-26 (the owner's own call: the target still
    lives in the `href`, so the card is exactly as clickable as
    before, it just stops repeating a raw hostname the description
    already conveys in French).
    """

    return f"""  <a class="card" href="{escape_text(link.url)}">
    <h2>{escape_text(link.name)}</h2>
    <p>{escape_text(link.description)}</p>
  </a>"""


# Palette and type sourced 2026-09-26 from persiaut-consulting.eu (the
# owner's own consulting site) rather than invented: navy #16335c and
# the muted slate #5b6b7d are the exact `color: rgb(...)` values Chrome
# DevTools reports computed on that site's `<h1 class="hero-title">`
# and `<p class="hero-subtitle">`; the border/background tones are
# pixel-sampled from its hero section. The heading typeface (Georgia)
# and body stack (the system-ui family) are that same page's own
# computed `font-family`, copied as-is — both are system fonts, so
# this page keeps rendering with no network access at all, the same
# constraint the vendored mark/lockup above already meets. Decided
# with the owner (three static pages — this one, `architecture.html`,
# `health.html` — share the same retouch; the AIStack mark itself is
# kept unchanged; the health-status badges below keep their
# green/amber/red meaning, only lightly retinted to sit next to navy
# rather than pure primary blue).
_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Helvetica, Arial, sans-serif;
  max-width: 900px; margin: 2rem auto;
  color: #1f2933; background: #f7f9fc; padding: 0 1rem;
}
header { text-align: center; margin-bottom: 2rem; }
.lockup { max-width: 340px; width: 100%; height: auto; }
.links {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}
.card {
  display: block; border: 1px solid #dde4ed; border-radius: 8px;
  padding: 1rem 1.2rem; text-decoration: none; color: inherit;
  background: #ffffff; transition: border-color .15s ease;
}
.card:hover { border-color: #16335c; }
.card h2 {
  margin: 0 0 .4rem; font-size: 1.05rem; color: #16335c;
  font-family: Georgia, "Times New Roman", Times, serif;
}
.card p { margin: 0 0 .6rem; font-size: .9rem; color: #5b6b7d; }
.health-cartouche {
  border: 1px solid #dde4ed; border-radius: 8px; padding: 1rem 1.2rem;
  margin-bottom: 1.4rem; background: #ffffff;
}
.cartouche-header {
  display: flex; align-items: baseline; justify-content: space-between;
  flex-wrap: wrap; gap: .6rem;
}
.cartouche-header h2 {
  margin: 0; font-size: 1.05rem; color: #16335c;
  font-family: Georgia, "Times New Roman", Times, serif;
}
.cartouche-score { font-size: .92rem; }
.cartouche-score-unavailable { color: #5b6b7d; }
.cartouche-technical-debt { font-size: .92rem; margin: .4rem 0 0; }
.cartouche-technical-debt-unavailable { color: #5b6b7d; }
.cartouche-badges {
  display: flex; flex-wrap: wrap; gap: .5rem; margin: .8rem 0 .6rem;
}
.domain-badge {
  font-size: .82rem; padding: .3rem .6rem; border-radius: 999px;
  border: 1px solid;
}
.badge {
  font-size: .72rem; font-weight: normal; padding: .15rem .5rem;
  border-radius: 999px; border: 1px solid;
}
.badge-not-instrumented, .domain-badge.badge-not-instrumented {
  background: #eef0f3; border-color: #5b6b7d; color: #5b6b7d;
}
.badge-clean, .domain-badge.badge-clean {
  background: #e4f3ea; border-color: #1f6d43; color: #1f6d43;
}
.badge-watch, .domain-badge.badge-watch {
  background: #faf1d8; border-color: #8a6100; color: #8a6100;
}
.badge-alert, .domain-badge.badge-alert {
  background: #f9e3e1; border-color: #9c2b2b; color: #9c2b2b;
}
.cartouche-link { font-size: .85rem; text-decoration: none; color: #16335c; }
.cartouche-link:hover { text-decoration: underline; }\
"""
