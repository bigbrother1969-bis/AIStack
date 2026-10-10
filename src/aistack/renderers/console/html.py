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

# Copied from `aistack.renderers.health.html` rather than imported: renderers
# do not import each other.
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
    """Render the console: the declared `ConsoleLink`s as one self-contained page.

    Links are routing decisions the owner declared; nothing here checks
    whether a target is reachable. With a `cockpit`, a summary banner shows
    the health score, the technical-debt card and one badge per domain;
    details stay on `/health.html`. Without one, no banner.

    The lockup and mark are embedded data URIs, so the page renders without
    internet access. Pure (no wall clock): `ConsoleHtmlArtifactGenerator`
    stamps when a copy was produced.

    `lang` selects the language (ADR-0010); `links` must already be resolved
    for it, and absolute links carry `?lang=` because the cookie does not
    cross hosts. Cards are grouped by `ConsoleLink.scope`. `version` is shown
    under the lockup when known.
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
    """The left column's text: what AIStack and this page are, links to help,
    legal notice and licence, and the copyright line when a publisher is declared.
    """

    copyright_line = (
        f'  <p class="aside-copyright">'
        f'{escape_text(t("console.aside.copyright", year=identity.copyright_year, publisher=identity.publisher))}'
        f"</p>\n"
        if identity is not None and identity.publisher
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

    # Only the alert state links, to the domain's section of `health.html`
    # (`id="domain-<slug>"`, same `domain_slug` on both sides). Clean and
    # not-instrumented badges already say everything.
    return (
        f'  <a class="domain-badge badge-alert" href="/health.html#domain-{domain_slug(domain.name)}" '
        f'title="{escape_text(t("console.tooltip.badge_alert", domain=name))}">'
        f'{escape_text(t("health.domain_state.findings", domain=name, count=len(domain.findings)))}'
        f"</a>"
    )


def _render_link_groups(links: tuple[ConsoleLink, ...], t: Translator) -> str:
    """Two foldable groups of cards, LAN and public, open by default.

    A group with no cards is not rendered.
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
    """One card: name and description, no visible URL (the target is in `href`).

    `card-{scope}` adds a left accent stripe for LAN vs public, deliberately
    not the health-state colours, which mean something else.
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


# Scope sentences older `console_links.yml` descriptions still end with; the
# card now writes that line itself.
_OLD_SCOPE_ENDINGS = (
    re.compile(r"\s*Accessible\s+uniquement\s+depuis\s+le\s+réseau\s+local\.?\s*$"),
    re.compile(r"\s*[—.,]?\s*AIStack web application,\s+LAN\s+listener\s+only(\s*\(ADR-\d+\))?\.?\s*$"),
)


def _path_of(url: str) -> str:
    from urllib.parse import urlsplit

    return urlsplit(url).path or "/"


# LAN cards carry their screen's path in `data-pending`; the script the web
# application adds for a signed-in person (`aistack.web.pending`) draws the
# badges. The page itself stays script-free.


def _without_scope_sentence(description: str, scope_line: str) -> str:
    """The description without a trailing scope sentence, which the card adds itself."""

    text = description.rstrip()
    if text.endswith(scope_line):
        text = text[: -len(scope_line)].rstrip()
    for ending in _OLD_SCOPE_ENDINGS:
        text = ending.sub("", text)
    return text


def _link_href(url: str, lang: str) -> str:
    """Absolute links get `?lang=` (ADR-0010: the cookie never crosses hosts);
    relative links are served by this console and stay as declared.
    """

    if url.startswith(("http://", "https://")):
        return with_language(url, lang)

    return url


# Palette and type from the owner's consulting site (navy #16335c,
# slate #5b6b7d, Georgia headings, system-ui body), shared by the three static
# pages. System fonts only, so the page works offline. Health badges keep
# their green/amber/red meaning. Width `min(96vw, 1600px)` (ADR-0011 § 26):
# adapts to the window and caps line length on wide screens.
_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Helvetica, Arial, sans-serif;
  max-width: min(96vw, 1600px); margin: 1.5rem auto;
  color: #1f2933; background: #f7f9fc; padding: 0 1rem;
}
/* Two columns. The lockup, the language switch and Settings sit in a left
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
/* Scope accent: a left-edge stripe, blue-gray for a LAN-only card,
   amber-gold for a public one, distinct from badge-watch's amber. */
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
