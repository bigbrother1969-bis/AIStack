"""
`plan.html` — the action plan (the owner's request, 2026-10-08): what to
do first to raise the health score and reduce the technical debt,
ranked by what it gains (`aistack.health.plan`). Reached from the two
score badges of the console and the Health cockpit; `#sante` and
`#dette` open the part each badge is about.

Server-side HTML, like `health.html`: no script. Pure — the same plan
renders to the same page.
"""

from __future__ import annotations

from urllib.parse import quote

from aistack.contracts.health_score import HealthScore
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.health.labels import bucket_label, domain_label
from aistack.health.plan import QUARANTINE, DebtAction, HealthAction
from aistack.i18n import Languages, Translator, default_languages, translator_for
from aistack.i18n.findings import finding_interpretation, finding_remediation
from aistack.renderers.assets import MARK_DATA_URI
from aistack.renderers.nav import PAGE_NAV_STYLE, render_page_nav
from aistack.renderers.text import escape_text

HEALTH_ANCHOR = "sante"
DEBT_ANCHOR = "dette"
PLAN_PAGE = "plan.html"


def plan_link(t: Translator, anchor: str) -> str:
    """Where a score's badge leads: the part of the plan it is about."""

    return f"/{PLAN_PAGE}?lang={t.lang}#{anchor}"

# Literal keys, so the catalog test sees every one of them.
HOW_TO = {
    "Stockage": "plan.how_to.storage",
    "Services": "plan.how_to.services",
    "Sauvegarde / PRA": "plan.how_to.backup",
    "GPU": "plan.how_to.gpu",
    "Tests PRA": "plan.how_to.pra_tests",
    "État persistant": "plan.how_to.uncovered_state",
    "Écarts d'inventaire": "plan.how_to.inventory_gap",
    "Hôtes": "plan.how_to.hosts",
    QUARANTINE: "plan.how_to.quarantine",
}


def _group_label(t: Translator, group: str) -> str:
    return t("plan.group.quarantine") if group == QUARANTINE else domain_label(t, group)


def _how(t: Translator, group: str) -> str:
    return t(HOW_TO.get(group, "plan.how_to.other"))


def _finding(
    finding: RuntimeFinding,
    domain: str,
    t: Translator,
    base_url: str | None,
    subject_counts: dict[str, int],
) -> str:
    diagnose = ""
    if base_url and domain != QUARANTINE:
        # The same routing key the Health cockpit's own link uses.
        key = finding.subject if subject_counts.get(finding.subject, 0) <= 1 else f"{domain}::{finding.subject}"
        diagnose = (
            f' <a class="diagnose" href="{escape_text(base_url)}/#finding-{quote(key, safe="")}" '
            f'title="{escape_text(t("plan.tooltip.diagnose"))}">{escape_text(t("plan.diagnose"))}</a>'
        )
    return (
        "    <li>"
        f"<strong>{escape_text(finding.subject)}</strong> — {escape_text(finding_interpretation(finding, t))}"
        f'<br><span class="remediation">→ {escape_text(finding_remediation(finding, t))}</span>'
        f"{diagnose}</li>"
    )


def _health_section(
    actions: tuple[HealthAction, ...],
    score: HealthScore | None,
    note: str,
    t: Translator,
    base_url: str | None,
    subject_counts: dict[str, int],
) -> str:
    parts = [f'<section id="{HEALTH_ANCHOR}">', f'<h2>{escape_text(t("plan.health_heading"))}</h2>']
    if score is None:
        parts.append(f'<p class="note">{escape_text(t("plan.health_unavailable", note=note))}</p>')
    else:
        parts.append(
            f'<p class="now">{escape_text(t("plan.health_now", value=score.value, bucket=bucket_label(t, score.bucket)))}</p>'
        )
    if score is not None and not actions:
        parts.append(f'<p>{escape_text(t("plan.health_none"))}</p>')
    for rank, action in enumerate(actions, 1):
        gain = (
            t("plan.gain", points=action.gain) if action.gain > 0 else t("plan.gain_zero")
        )
        one = ""
        if len(action.findings) > 1:
            one = t("plan.gain_one", points=action.gain_one) if action.gain_one > 0 else t("plan.gain_one_zero")
        parts.append(
            '<article class="action">'
            f'<h3><span class="rank">{rank}</span> {escape_text(domain_label(t, action.domain))} '
            f'<span class="gain">{escape_text(gain)}</span></h3>'
            + (f'<p class="note">{escape_text(one)}</p>' if one else "")
            + f'<p class="how"><strong>{escape_text(t("plan.how"))}</strong> {escape_text(_how(t, action.domain))}</p>'
            + f'<p class="count">{escape_text(t("plan.findings", count=len(action.findings)))}</p>'
            + "<ul>\n"
            + "\n".join(_finding(finding, action.domain, t, base_url, subject_counts) for finding in action.findings)
            + "\n</ul></article>"
        )
    parts.append("</section>")
    return "\n".join(parts)


def _debt_section(
    actions: tuple[DebtAction, ...],
    score: TechnicalDebtScore | None,
    note: str,
    weight: int,
    t: Translator,
    base_url: str | None,
    subject_counts: dict[str, int],
) -> str:
    parts = [f'<section id="{DEBT_ANCHOR}">', f'<h2>{escape_text(t("plan.debt_heading"))}</h2>']
    if score is None:
        parts.append(f'<p class="note">{escape_text(t("plan.debt_unavailable", note=note))}</p>')
    else:
        parts.append(
            f'<p class="now">{escape_text(t("plan.debt_now", value=score.value, bucket=bucket_label(t, score.bucket), weight=weight))}</p>'
        )
    if score is not None and not actions:
        parts.append(f'<p>{escape_text(t("plan.debt_none"))}</p>')
    for rank, action in enumerate(actions, 1):
        waiting = f'<p class="note">{escape_text(t("plan.waiting"))}</p>' if action.waiting else ""
        parts.append(
            f'<article class="action{" waiting" if action.waiting else ""}">'
            f'<h3><span class="rank">{rank}</span> {escape_text(_group_label(t, action.group))} '
            f'<span class="gain">{escape_text(t("plan.debt_gain", points=action.gain))}</span></h3>'
            f"{waiting}"
            f'<p class="how"><strong>{escape_text(t("plan.how"))}</strong> {escape_text(_how(t, action.group))}</p>'
            f'<p class="count">{escape_text(t("plan.findings", count=len(action.findings)))}</p>'
            "<ul>\n"
            + "\n".join(_finding(finding, action.group, t, base_url, subject_counts) for finding in action.findings)
            + "\n</ul></article>"
        )
    parts.append("</section>")
    return "\n".join(parts)


def render_plan(
    health: tuple[HealthAction, ...],
    debt: tuple[DebtAction, ...],
    *,
    score: HealthScore | None,
    score_note: str = "",
    debt_score: TechnicalDebtScore | None,
    debt_note: str = "",
    weight: int = 0,
    subject_counts: dict[str, int] | None = None,
    troubleshooting_base_url: str | None = None,
    lang: str | None = None,
    languages: Languages | None = None,
) -> str:
    t = translator_for(lang)
    declared = languages if languages is not None else default_languages()
    counts = subject_counts or {}
    return f"""<!doctype html>
<html lang="{t.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_text(t("plan.title"))}</title>
<link rel="icon" href="{MARK_DATA_URI}">
<style>
{_STYLE}
{PAGE_NAV_STYLE}
</style>
</head>
<body>
{render_page_nav(t, declared, t.lang)}
<header>
  <h1>{escape_text(t("plan.heading"))}</h1>
  <p>{escape_text(t("plan.intro"))}</p>
  <p class="meta">{escape_text(t("plan.generated"))} <a href="/health.html?lang={t.lang}" title="{escape_text(t("plan.tooltip.back_to_health"))}">{escape_text(t("plan.back_to_health"))}</a></p>
</header>
{_health_section(health, score, score_note, t, troubleshooting_base_url, counts)}
{_debt_section(debt, debt_score, debt_note, weight, t, troubleshooting_base_url, counts)}
</body>
</html>
"""


_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Helvetica, Arial, sans-serif;
  max-width: min(96vw, 1200px); margin: 2rem auto;
  color: #1f2933; background: #f7f9fc; padding: 0 1rem;
}
h1, h2, h3 { font-family: Georgia, "Times New Roman", Times, serif; color: #16335c; }
header { margin-bottom: 1.4rem; }
.meta, .note, .count { color: #5b6b7d; font-size: .9rem; }
section { margin-bottom: 2rem; }
.now { font-weight: 600; }
.action {
  border: 1px solid #dde4ed; border-radius: 8px; padding: .9rem 1.2rem;
  margin-bottom: 1rem; background: #fff;
}
.action.waiting { background: #fafafa; }
.action h3 { margin: 0 0 .4rem; font-size: 1.05rem; display: flex; flex-wrap: wrap; align-items: center; gap: .6rem; }
.rank {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.6rem; height: 1.6rem; border-radius: 50%;
  background: #16335c; color: #fff; font-family: inherit; font-size: .85rem;
}
.gain {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: .8rem; font-weight: 600; padding: .15rem .55rem; border-radius: 999px;
  background: #e4f3ea; color: #1f6d43; border: 1px solid #1f6d43;
}
.how { margin: .4rem 0; }
ul { margin: .3rem 0 0; padding-left: 1.2rem; }
li { margin-bottom: .5rem; }
.remediation { color: #16335c; }
.diagnose { margin-left: .4rem; font-size: .85rem; }
"""
