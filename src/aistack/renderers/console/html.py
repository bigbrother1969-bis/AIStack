from __future__ import annotations

import re

from aistack.contracts.console_link import LAN, PUBLIC, ConsoleLink
from aistack.contracts.health_score import (
    ACTION_REQUIRED,
    EXCELLENT,
    TO_WATCH,
    HealthScore,
)
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.labels import bucket_label, domain_label
from aistack.i18n import (
    Languages,
    Translator,
    default_languages,
    translator_for,
    with_language,
)
from aistack.console.identity import ConsoleIdentity
from aistack.renderers.assets import LOCKUP_DATA_URI, MARK_DATA_URI
from aistack.renderers.console.pages import HELP_PATH, LEGAL_PATH, LICENSE_PATH
from aistack.renderers.nav import PAGE_NAV_STYLE, render_page_nav
from aistack.renderers.text import domain_slug, escape_text
from aistack.renderers.plan.html import DEBT_ANCHOR, HEALTH_ANCHOR, plan_link

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
    lang: str | None = None,
    languages: Languages | None = None,
    identity: ConsoleIdentity | None = None,
    version: str = "",
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
    (`aistack.renderers.assets.LOCKUP_DATA_URI`) is the header
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

    **`lang`, added 2026-09-27** (ADR-0010): the page is written in
    `lang`, the reference language when `None` — whose output is
    exactly what this page said before localization, apart from the
    navigation strip (Settings link, language switch) every served
    page now carries. `links` are expected already resolved for the
    same language (`load_console_links_yaml(..., lang=...)`); each
    absolute link carries `?lang=` so the language follows the visitor
    to a mini-app on another host, where the cookie cannot.

    **Grouped by `ConsoleLink.scope` since 2026-09-30** (the owner:
    "on regroupera les cartes 'LAN' et les cartes 'Internet'") — see
    `_render_link_groups` below.

    **`version`, added 2026-10-09** (the owner: "mettre le numéro de
    version en cours sous le logo AIStack sur la page console"): the
    version the installed AIStack declares, one line under the lockup;
    nothing when it is empty or unknown. Passed in, never read here, so
    the function stays pure.
    """

    t = translator_for(lang)
    declared = languages if languages is not None else default_languages()

    link_groups_html = _render_link_groups(links, t)
    cartouche_html = (
        _render_health_cartouche(
            cockpit, score, score_note, technical_debt_score, technical_debt_note, t
        )
        if cockpit is not None
        else ""
    )

    return f"""<!doctype html>
<html lang="{t.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_text(t("console.title"))}</title>
<link rel="icon" href="{MARK_DATA_URI}">
<style>
{_STYLE}
{PAGE_NAV_STYLE}
</style>
</head>
<body id="top">
<div class="console-layout">
<aside class="console-aside">
  <a href="#top" title="{escape_text(t("console.tooltip.lockup"))}"><img class="lockup" src="{LOCKUP_DATA_URI}" alt="{escape_text(t("console.lockup_alt"))}"></a>
{_render_version(t, version)}{_render_aside_text(t, identity)}
  {render_page_nav(t, declared, t.lang, back_to_console=False)}
</aside>
<div class="console-content">
{cartouche_html}

<main class="links">
{link_groups_html}
</main>
</div>
</div>
</body>
</html>
"""


def _render_version(t: Translator, version: str) -> str:
    """The running version under the lockup, or nothing when unknown."""

    if not version or version == "unknown":
        return ""
    return f'  <p class="aside-version">{escape_text(t("console.version", version=version))}</p>\n'


def _render_aside_text(t: Translator, identity: ConsoleIdentity | None) -> str:
    """
    What the left column says between the lockup and the language
    switch (the owner, 2026-10-03: "du texte explicatif et des liens
    (copyright, mentions légales, aide...) [...] pour meubler et
    améliorer l'appropriation"): two sentences on what AIStack and this
    page are, the help, legal-notice and licence pages, and the
    copyright line when the publisher is declared.
    """

    copyright_line = (
        f'  <p class="aside-copyright">'
        f'{escape_text(t("console.aside.copyright", year=identity.copyright_year, publisher=identity.publisher))}'
        f"</p>\n"
        if identity is not None
        else ""
    )

    links = "\n".join(
        f'    <a href="{path}" title="{escape_text(t(f"console.tooltip.{key}"))}">'
        f'{escape_text(t(f"console.aside.{key}"))}</a>'
        for key, path in (("help", HELP_PATH), ("legal", LEGAL_PATH), ("license", LICENSE_PATH))
    )

    return (
        f'  <p class="aside-intro">{escape_text(t("console.aside.intro"))}</p>\n'
        f'  <p class="aside-guide">{escape_text(t("console.aside.guide"))}</p>\n'
        f'  <nav class="aside-links">\n{links}\n  </nav>\n'
        f"{copyright_line}"
    )


def _render_health_cartouche(
    cockpit: HealthCockpit,
    score: HealthScore | None,
    score_note: str,
    technical_debt_score: TechnicalDebtScore | None,
    technical_debt_note: str,
    t: Translator,
) -> str:
    if not cockpit.domains:
        return ""

    score_html = _render_cartouche_score(score, score_note, t)
    technical_debt_html = _render_cartouche_technical_debt(
        technical_debt_score, technical_debt_note, t
    )
    badges = "\n".join(_render_domain_badge(domain, t) for domain in cockpit.domains)

    return f"""<section class="health-cartouche" title="{escape_text(t("console.tooltip.cartouche"))}">
  <div class="cartouche-header">
    <h2>{escape_text(t("console.cartouche.title"))}</h2>
    {score_html}
  </div>
  {technical_debt_html}
  <div class="cartouche-badges">
{badges}
  </div>
  <a class="cartouche-link" href="/health.html" title="{escape_text(t("console.tooltip.detail_link"))}">{escape_text(t("console.cartouche.detail_link"))}</a>
</section>"""


def _render_cartouche_score(
    score: HealthScore | None, score_note: str, t: Translator
) -> str:
    if score is not None:
        badge_class = _BUCKET_BADGE_CLASS[score.bucket]

        return (
            f'<span class="cartouche-score" title="{escape_text(t("console.tooltip.score"))}">'
            f'{escape_text(t("console.cartouche.score"))} '
            f'<strong>{score.value}/100</strong> '
            f'<a class="badge {badge_class}" href="{plan_link(t, HEALTH_ANCHOR)}" '
            f'title="{escape_text(t("plan.tooltip.badge"))}">'
            f"{escape_text(bucket_label(t, score.bucket))}</a></span>"
        )

    if score_note:
        return (
            f'<span class="cartouche-score cartouche-score-unavailable">'
            f'{escape_text(t("console.cartouche.score_unavailable", note=score_note))}'
            f"</span>"
        )

    return ""


def _render_cartouche_technical_debt(
    score: TechnicalDebtScore | None, note: str, t: Translator
) -> str:
    if score is not None:
        badge_class = _BUCKET_BADGE_CLASS[score.bucket]

        return (
            f'<div class="cartouche-technical-debt" '
            f'title="{escape_text(t("console.tooltip.technical_debt"))}">'
            f'{escape_text(t("console.cartouche.technical_debt"))} '
            f'<strong>{score.value}/100</strong> '
            f'<a class="badge {badge_class}" href="{plan_link(t, DEBT_ANCHOR)}" '
            f'title="{escape_text(t("plan.tooltip.badge"))}">'
            f"{escape_text(bucket_label(t, score.bucket))}</a></div>"
        )

    if note:
        return (
            f'<div class="cartouche-technical-debt '
            f'cartouche-technical-debt-unavailable">'
            f'{escape_text(t("console.cartouche.technical_debt_unavailable", note=note))}'
            f"</div>"
        )

    return ""


def _render_domain_badge(domain: HealthDomain, t: Translator) -> str:
    name = domain_label(t, domain.name)

    if not domain.instrumented:
        return (
            f'  <span class="domain-badge badge-not-instrumented" '
            f'title="{escape_text(t("console.tooltip.badge_not_instrumented", domain=name))}">'
            f'{escape_text(t("health.domain_state.not_instrumented", domain=name))}</span>'
        )

    if not domain.findings:
        return (
            f'  <span class="domain-badge badge-clean" '
            f'title="{escape_text(t("console.tooltip.badge_clean", domain=name))}">'
            f'{escape_text(t("health.domain_state.clean", domain=name))}</span>'
        )

    # A link, not a plain span, since 2026-09-30 — the owner, reading
    # this exact badge: "les findings en rouge doivent être cliquables
    # et doivent diriger vers une explication". `console.html` only
    # shows a domain's count, never its individual findings — the
    # detail lives at `health.html`, this anchors straight to that
    # domain's own section there (`aistack.renderers.health.html`'s
    # own `id="domain-<slug>"`, the same `domain_slug` computed the
    # same way on both sides). Only the alert state links: a clean or
    # not-instrumented domain has nothing further to read there that
    # this badge does not already say.
    return (
        f'  <a class="domain-badge badge-alert" href="/health.html#domain-{domain_slug(domain.name)}" '
        f'title="{escape_text(t("console.tooltip.badge_alert", domain=name))}">'
        f'{escape_text(t("health.domain_state.findings", domain=name, count=len(domain.findings)))}'
        f"</a>"
    )


def _render_link_groups(links: tuple[ConsoleLink, ...], t: Translator) -> str:
    """
    Split the declared cards into two foldable groups by
    `ConsoleLink.scope` — added 2026-09-30, the owner's own request
    ("on regroupera les cartes 'LAN' et les cartes 'Internet'").

    Same `<details open><summary>title <span class="…-count">N</span>
    </summary>…</details>` disclosure `timemachine_ui/templates/
    ribbon.html` already established for its own two categories
    (ADR-0011 §26, patch 0082) — open by default here too (this page
    has 7 cards total across the two groups, not Time Machine's dozens
    of streams, so there is nothing to hide by default). Coded
    independently in this module rather than imported: each renderer
    in this package keeps its own `_STYLE`, "no shared stylesheet, no
    cross-renderer import" (see this module's own docstring above),
    and the same holds for the markup that pairs with it.

    A group with no cards is not rendered at all — the same
    None/empty-renders-nothing idiom `_render_health_cartouche`
    already holds for a cockpit with no domains. `console_links.yml`
    declares at least one card of each scope today, but nothing here
    assumes that stays true.
    """

    groups = [
        rendered
        for rendered in (
            _render_link_group(
                LAN,
                t("console.groups.lan_title"),
                tuple(link for link in links if link.scope == LAN),
                t,
            ),
            _render_link_group(
                PUBLIC,
                t("console.groups.public_title"),
                tuple(link for link in links if link.scope == PUBLIC),
                t,
            ),
        )
        if rendered
    ]

    return "\n".join(groups)


def _render_link_group(
    scope: str, title: str, links: tuple[ConsoleLink, ...], t: Translator
) -> str:
    if not links:
        return ""

    cards = "\n".join(_render_link(link, t) for link in links)

    return f"""  <details class="link-group link-group-{scope}" open>
    <summary title="{escape_text(t("console.tooltip.group"))}">{escape_text(title)} <span class="link-group-count">{len(links)}</span></summary>
    <div class="link-group-grid">
{cards}
    </div>
  </details>"""


def _render_link(link: ConsoleLink, t: Translator) -> str:
    """
    The card shows the name and description only — no visible URL
    text, since 2026-09-26 (the owner's own call: the target still
    lives in the `href`, so the card is exactly as clickable as
    before, it just stops repeating a raw hostname the description
    already conveys in French).

    **`card-{link.scope}` added 2026-09-30** — the owner's "bandeau de
    couleur différent" for a LAN vs a public card, a left-edge accent
    stripe (`_STYLE` below) deliberately not drawn from the
    `badge-clean`/`badge-watch`/`badge-alert` health-state colors
    already used elsewhere on this page: a LAN card is not "healthy"
    and a public card is not "in alert", so reusing that triptych here
    would misuse a meaning it already carries.
    """

    tooltip = t(
        "console.tooltip.card_lan" if link.scope == LAN else "console.tooltip.card_public",
        name=link.name,
    )

    scope_line = t("console.card_scope_lan") if link.scope == LAN else ""
    description = _without_scope_sentence(link.description, scope_line) if scope_line else link.description
    scope_html = f'\n      <p class="card-scope"><em>{escape_text(scope_line)}</em></p>' if scope_line else ""
    ai_html = (
        f'\n      <p class="card-ai"><span class="ai-mark" title="{escape_text(t("console.ai_mark_title"))}">'
        f'{escape_text(t("console.ai_mark"))}</span> {escape_text(link.ai)}</p>'
        if link.ai
        else ""
    )

    pending = f' data-pending="{escape_text(_path_of(link.url))}"' if link.scope == LAN else ""
    return f"""    <a class="card card-{link.scope}"{pending} href="{escape_text(_link_href(link.url, t.lang))}" title="{escape_text(tooltip)}">
      <h2>{escape_text(link.name)}</h2>
      <p>{escape_text(description)}</p>{ai_html}{scope_html}
    </a>"""


# What a description written before 2026-10-09 still ends with: the
# console now says it on the card's own last line (the owner's call).
_OLD_SCOPE_ENDINGS = (
    re.compile(r"\s*Accessible\s+uniquement\s+depuis\s+le\s+réseau\s+local\.?\s*$"),
    re.compile(r"\s*[—.,]?\s*AIStack web application,\s+LAN\s+listener\s+only(\s*\(ADR-\d+\))?\.?\s*$"),
)


def _path_of(url: str) -> str:
    from urllib.parse import urlsplit

    return urlsplit(url).path or "/"


# What waits for the owner behind a card (2026-10-10): the card carries
# its screen's path in `data-pending`; the notice script the local
# network listener adds for a signed-in person
# (`aistack.web.notifications`) asks `/pending` and draws the pastille.
# The page itself stays script-free.


def _without_scope_sentence(description: str, scope_line: str) -> str:
    """The description without the scope sentence at its end — a
    `console_links.yml` copied before the console wrote that line
    itself still carries it, and the card would say it twice."""

    text = description.rstrip()
    if text.endswith(scope_line):
        text = text[: -len(scope_line)].rstrip()
    for ending in _OLD_SCOPE_ENDINGS:
        text = ending.sub("", text)
    return text


def _link_href(url: str, lang: str) -> str:
    """
    An absolute link — a mini-app on another host — carries the
    current language in its query string (ADR-0010: the cookie never
    crosses host names). A relative link stays as declared: it is
    served by this same console, which already knows the language
    from its own cookie.
    """

    if url.startswith(("http://", "https://")):
        return with_language(url, lang)

    return url


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
#
# Width (ADR-0011 §26, 1.5.2 graphic-debt cadrage, 2026-09-29): a
# fixed 900px column, no wider on a wide monitor than on a laptop —
# the owner's own finding, from the Time Machine ribbon's own
# crowding, extended here at the owner's own broader request ("toute
# l'appli") to this page too, not just the mini-app that found it.
# `min(96vw, 1600px)` adapts to the real window instead of sitting
# fixed, while still capping line length on an ultra-wide monitor.
_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Helvetica, Arial, sans-serif;
  max-width: min(96vw, 1600px); margin: 1.5rem auto;
  color: #1f2933; background: #f7f9fc; padding: 0 1rem;
}
/* Two columns, 2026-10-03 (the owner: "le logo en haut prend trop de
   place : je préférerais le mettre à gauche et réorganiser la page à
   droite"). The lockup, the language switch and Settings sit in a left
   column that stays in view while the right one scrolls; under 900px
   the column becomes a compact band above the content. */
.console-layout {
  display: grid; grid-template-columns: 220px minmax(0, 1fr);
  gap: 2rem; align-items: start;
}
.console-aside {
  position: sticky; top: 1.5rem;
  display: flex; flex-direction: column; align-items: center; gap: 1rem;
}
.console-aside .lockup { width: 100%; max-width: 220px; height: auto; }
.aside-version { margin: -.25rem 0 0; font-size: .8rem; color: #5b6b7d; text-align: center; width: 100%; max-width: 220px; }
.console-aside .page-nav {
  flex-direction: column; align-items: center; justify-content: flex-start;
  gap: .6rem; margin: 0;
}
.console-content { min-width: 0; }
.aside-intro, .aside-guide {
  margin: 0; font-size: .85rem; line-height: 1.45; color: #5b6b7d; text-align: left;
}
.aside-intro { color: #1f2933; }
.aside-links {
  display: flex; flex-direction: column; align-items: flex-start; gap: .35rem;
  width: 100%; font-size: .88rem;
}
.aside-links a { color: #16335c; text-decoration: none; }
.aside-links a:hover { text-decoration: underline; }
.aside-copyright { margin: 0; font-size: .75rem; color: #5b6b7d; text-align: left; width: 100%; }
@media (max-width: 900px) {
  .console-layout { grid-template-columns: 1fr; gap: 1rem; }
  .console-aside {
    position: static; flex-direction: row; justify-content: space-between;
  }
  .console-aside .lockup { max-width: 140px; }
  .console-aside .page-nav { flex-direction: row; }
  .console-aside { flex-wrap: wrap; }
  .aside-guide { display: none; }
  .aside-links { flex-direction: row; flex-wrap: wrap; gap: .8rem; }
}
.links { margin: 0; }
.link-group {
  border: 1px solid #dde4ed; border-radius: 8px; background: #fafbfc;
  margin: 0 0 1.2rem; padding: 0 1rem 1rem;
}
.link-group > summary {
  cursor: pointer; padding: .8rem 0; list-style: none;
  display: flex; align-items: center; gap: .5rem;
  font-weight: 600; font-size: 1rem; color: #16335c;
}
.link-group > summary::-webkit-details-marker { display: none; }
.link-group > summary::before {
  content: "\\25B8"; display: inline-block; color: #888; font-size: .75rem;
  transition: transform .1s ease;
}
.link-group[open] > summary::before { transform: rotate(90deg); }
.link-group-count {
  font-size: .75rem; font-weight: 600; padding: .05rem .5rem;
  border-radius: 10px; background: #e6f0ff; color: #16335c;
}
.link-group-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}
.card {
  display: block; border: 1px solid #dde4ed; border-radius: 8px;
  padding: 1rem 1.2rem; text-decoration: none; color: inherit;
  background: #ffffff; transition: border-color .15s ease;
}
.card:hover { border-color: #16335c; }
.card[data-pending] { position: relative; }
.pending-mark {
  position: absolute; top: .55rem; right: .6rem; min-width: 1.4rem; height: 1.4rem;
  padding: 0 .35rem; box-sizing: border-box; border-radius: .7rem;
  background: #c2410c; color: #ffffff; font: 700 .78rem/1.4rem system-ui, sans-serif;
  text-align: center; box-shadow: 0 0 0 2px #ffffff;
}
.card h2 {
  margin: 0 0 .4rem; font-size: 1.05rem; color: #16335c;
  font-family: Georgia, "Times New Roman", Times, serif;
}
.card p { margin: 0 0 .6rem; font-size: .9rem; color: #5b6b7d; }
.card .card-ai { margin: .4rem 0 0; font-size: .85rem; color: #16335c; }
.card .ai-mark {
  display: inline-block; font-size: .7rem; font-weight: 700; letter-spacing: .04em;
  padding: .05rem .4rem; margin-right: .3rem; border-radius: 4px;
  background: #16335c; color: #ffffff; vertical-align: 1px;
}
.card .card-scope { margin: .4rem 0 0; font-size: .85rem; color: #3d5a73; }
/* Scope accent, 2026-09-30 (the owner's "bandeau de couleur
   différent") — a left-edge stripe, deliberately not the health
   triptych above: blue-gray for a LAN-only card, amber-gold for a
   public one, values distinct from badge-watch's own amber
   (#8a6100/#faf1d8) so the two are never mistaken for one meaning. */
.card-lan { border-left: 4px solid #3d5a73; }
.card-public { border-left: 4px solid #a3791a; }
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
  border: 1px solid; display: inline-block; text-decoration: none;
}
a.domain-badge.badge-alert { cursor: pointer; }
a.domain-badge.badge-alert:hover { filter: brightness(0.96); text-decoration: underline; }
a.badge { text-decoration: none; cursor: pointer; }
a.badge:hover { filter: brightness(0.96); text-decoration: underline; }
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
