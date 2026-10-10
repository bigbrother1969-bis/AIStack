from __future__ import annotations

from urllib.parse import quote

from aistack.contracts.health_score import (
    ACTION_REQUIRED,
    EXCELLENT,
    TO_WATCH,
    HealthScore,
)
from aistack.contracts.runtime_finding import CitedReading, MatchedLine, RuntimeFinding
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.labels import bucket_label, domain_label
from aistack.i18n.findings import (
    finding_confidence,
    finding_interpretation,
    finding_remediation,
)
from aistack.i18n import Languages, Translator, default_languages, translator_for
from aistack.renderers.assets import MARK_DATA_URI
from aistack.renderers.nav import PAGE_NAV_STYLE, render_page_nav
from aistack.renderers.text import domain_slug, escape_text
from aistack.renderers.plan.html import DEBT_ANCHOR, HEALTH_ANCHOR, plan_link

_BUCKET_BADGE_CLASS = {
    EXCELLENT: "badge-clean",
    TO_WATCH: "badge-watch",
    ACTION_REQUIRED: "badge-alert",
}


def render_html(
    cockpit: HealthCockpit,
    score: HealthScore | None = None,
    score_note: str = "",
    technical_debt_score: TechnicalDebtScore | None = None,
    technical_debt_note: str = "",
    lang: str | None = None,
    languages: Languages | None = None,
    troubleshooting_base_url: str | None = None,
) -> str:
    """Render a `HealthCockpit` snapshot as one self-contained HTML page.

    `score` and `technical_debt_score` are computed by the caller (OPS-0008,
    OPS-0004) and only displayed here. Each is optional: `None` with a note
    shows the reason it is unavailable, `None` without a note shows nothing.
    The technical-debt card sits right after the global score because it
    spans domains.

    No client-side script: findings are already text. Pure (no wall clock),
    so `HealthHtmlArtifactGenerator` stamps when a copy was produced.

    With `troubleshooting_base_url`, each finding links to the LAN
    troubleshooting assistant. The routing key is the subject, or
    `<domain>::<subject>` when several domains name it, matching
    `aistack.troubleshooting.findings.QualifiedFinding`. The assistant's own
    CPU-consumption findings are not visible here, so a rare collision ends
    in a "not found" redirect there, never a wrong action.
    """

    t = translator_for(lang)
    declared = languages if languages is not None else default_languages()

    domain_count = len(cockpit.domains)
    instrumented_count = sum(1 for domain in cockpit.domains if domain.instrumented)

    subject_counts: dict[str, int] = {}
    for domain in cockpit.domains:
        for finding in domain.findings:
            subject_counts[finding.subject] = subject_counts.get(finding.subject, 0) + 1

    sections = "\n".join(
        _render_domain(domain, t, troubleshooting_base_url, subject_counts)
        for domain in cockpit.domains
    )

    return f"""<!doctype html>
<html lang="{t.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_text(t("health.page.title"))}</title>
<link rel="icon" href="{MARK_DATA_URI}">
<style>
{_STYLE}
{PAGE_NAV_STYLE}
</style>
</head>
<body>
{render_page_nav(t, declared, t.lang)}
<header>
  <h1>{escape_text(t("health.page.heading"))}</h1>
  <p class="meta">
    {escape_text(t("health.page.instrumented", instrumented=instrumented_count, total=domain_count))}
  </p>
  {_render_score(score, score_note, t)}
</header>

{_render_technical_debt(technical_debt_score, technical_debt_note, t)}
{sections}
</body>
</html>
"""


def _render_score(score: HealthScore | None, score_note: str, t: Translator) -> str:
    if score is not None:
        badge_class = _BUCKET_BADGE_CLASS[score.bucket]
        measured = t(
            "health.page.score_measured",
            measured=score.measured_domains,
            total=score.total_domains,
        )

        return (
            f'<p class="score">{escape_text(t("health.page.score"))} '
            f"<strong>{score.value}/100</strong> "
            f'<a class="badge {badge_class}" href="{plan_link(t, HEALTH_ANCHOR)}" '
            f'title="{escape_text(t("plan.tooltip.badge"))}">'
            f"{escape_text(bucket_label(t, score.bucket))}</a> "
            f"— {escape_text(measured)}"
            f"</p>"
        )

    if score_note:
        return (
            f'<p class="score score-unavailable">'
            f'{escape_text(t("health.page.score_unavailable", note=score_note))}'
            f"</p>"
        )

    return ""


def _render_technical_debt(
    score: TechnicalDebtScore | None, note: str, t: Translator
) -> str:
    heading = escape_text(t("health.page.technical_debt"))

    if score is not None:
        badge_class = _BUCKET_BADGE_CLASS[score.bucket]
        findings = t("health.page.technical_debt_findings", count=len(score.findings))

        return f"""<section class="technical-debt">
  <h2>{heading} <a class="badge {badge_class}" href="{plan_link(t, DEBT_ANCHOR)}" title="{escape_text(t("plan.tooltip.badge"))}">{escape_text(bucket_label(t, score.bucket))}</a></h2>
  <p class="score">
    <strong>{score.value}/100</strong> — {escape_text(findings)}
    {escape_text("OPS-0004/technical-debt")}
  </p>
</section>"""

    if note:
        unavailable = t("health.page.technical_debt_unavailable", note=note)

        return f"""<section class="technical-debt technical-debt-unavailable">
  <h2>{heading}</h2>
  <p class="note score-unavailable">{escape_text(unavailable)}</p>
</section>"""

    return ""


def _render_domain(
    domain: HealthDomain,
    t: Translator,
    troubleshooting_base_url: str | None,
    subject_counts: dict[str, int],
) -> str:
    name = escape_text(domain_label(t, domain.name))
    anchor = f'id="domain-{domain_slug(domain.name)}"'

    if not domain.instrumented:
        return f"""<section class="domain domain-not-instrumented" {anchor}>
  <h2>{name} <span class="badge badge-not-instrumented">{escape_text(t("health.page.not_instrumented"))}</span></h2>
  <p class="note">{escape_text(domain.note)}</p>
</section>"""

    if not domain.findings:
        return f"""<section class="domain domain-clean" {anchor}>
  <h2>{name} <span class="badge badge-clean">{escape_text(t("health.page.clean"))}</span></h2>
</section>"""

    findings = "\n".join(
        _render_finding(finding, t, troubleshooting_base_url, domain.name, subject_counts)
        for finding in domain.findings
    )
    count = escape_text(t("health.page.findings", count=len(domain.findings)))

    return f"""<section class="domain domain-alert" {anchor}>
  <h2>{name} <span class="badge badge-alert">{count}</span></h2>
  {findings}
</section>"""


def _render_finding(
    finding: RuntimeFinding,
    t: Translator,
    troubleshooting_base_url: str | None,
    domain_name: str,
    subject_counts: dict[str, int],
) -> str:
    """Only the labels around a finding are translated (ADR-0010 § 4); its own
    fields are shown exactly as the runtime qualified them.
    """

    qualifications = (
        f'<p class="qualifications">{escape_text(t("health.page.qualifications"))} '
        f"{escape_text(', '.join(finding.qualifications))}</p>"
        if finding.qualifications
        else ""
    )

    diagnose = ""
    if troubleshooting_base_url:
        key = (
            finding.subject
            if subject_counts.get(finding.subject, 0) <= 1
            else f"{domain_name}::{finding.subject}"
        )
        # A link, not a form (ADR-0014 § 3): starting a diagnosis is an
        # administrator action on the Troubleshooting screen itself, with its own
        # session and token.
        diagnose = (
            f'<a class="diagnose" '
            f'href="{escape_text(troubleshooting_base_url)}/#finding-{quote(key, safe="")}" '
            f'title="{escape_text(t("health.tooltip.diagnose"))}">'
            f'{escape_text(t("health.page.diagnose"))}</a>'
        )

    return f"""  <article class="finding">
    <h3>{escape_text(finding.subject)} — {escape_text(finding.signature)}</h3>
    <p class="interpretation">{escape_text(finding_interpretation(finding, t))}</p>
    <p class="remediation">→ {escape_text(finding_remediation(finding, t))}</p>
    <p class="confidence">{escape_text(t("health.page.confidence"))} {escape_text(finding_confidence(finding, t))} —
      {escape_text(t("health.page.grounding"))} {escape_text(finding.grounding)}</p>
    {qualifications}
    <p class="evidence">{_evidence_summary(finding.evidence, t)}</p>
    {diagnose}
  </article>"""


def _evidence_summary(
    evidence: tuple[MatchedLine | CitedReading, ...], t: Translator
) -> str:
    readings = [item for item in evidence if isinstance(item, CitedReading)]
    lines = [item for item in evidence if isinstance(item, MatchedLine)]

    parts = []
    if readings:
        parts.append(
            escape_text(t("health.page.readings", count=len(readings)))
            + " "
            + escape_text(
                ", ".join(f"{item.provider} → {item.reading!r}" for item in readings)
            )
        )
    if lines:
        parts.append(escape_text(t("health.page.log_lines", count=len(lines))))

    return (
        " — ".join(parts)
        if parts
        else escape_text(t("health.page.evidence", count=len(evidence)))
    )


# Same palette as `aistack.renderers.console.html` (see its comment), kept
# identical across the static pages by design, not shared code. Width
# `min(96vw, 1600px)` as there (ADR-0011 § 26).
_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Helvetica, Arial, sans-serif;
  max-width: min(96vw, 1600px); margin: 2rem auto;
  color: #1f2933; background: #f7f9fc; padding: 0 1rem;
}
h1, h2, h3 {
  font-family: Georgia, "Times New Roman", Times, serif;
  color: #16335c;
}
header { margin-bottom: 1.4rem; }
.meta { color: #5b6b7d; font-size: .85rem; }
.domain {
  border: 1px solid #dde4ed; border-radius: 8px; padding: 1rem 1.2rem;
  margin-bottom: 1rem;
}
.domain h2 { margin: 0 0 .4rem; font-size: 1.1rem; display: flex; align-items: center; gap: .6rem; }
.badge {
  font-size: .72rem; font-weight: normal; padding: .15rem .5rem;
  border-radius: 999px; border: 1px solid;
}
.badge-not-instrumented { background: #eef0f3; border-color: #5b6b7d; color: #5b6b7d; }
.badge-clean { background: #e4f3ea; border-color: #1f6d43; color: #1f6d43; }
.badge-watch { background: #faf1d8; border-color: #8a6100; color: #8a6100; }
.badge-alert { background: #f9e3e1; border-color: #9c2b2b; color: #9c2b2b; }
a.badge { text-decoration: none; cursor: pointer; }
a.badge:hover { filter: brightness(.95); text-decoration: underline; }
.domain-not-instrumented { background: #fafafa; }
.domain-clean { background: #f7fdf6; }
.domain-alert { background: #fff8f8; }
.note { color: #5b6b7d; font-size: .9rem; }
.score { font-size: .95rem; margin: .4rem 0 0; }
.score-unavailable { color: #5b6b7d; }
.technical-debt {
  border: 1px solid #dde4ed; border-radius: 8px; padding: 1rem 1.2rem;
  margin-bottom: 1rem; background: #ffffff;
}
.technical-debt h2 { margin: 0 0 .4rem; font-size: 1.1rem; display: flex; align-items: center; gap: .6rem; }
.technical-debt-unavailable { background: #fafafa; }
.finding {
  border-top: 1px solid #dde4ed; padding-top: .6rem; margin-top: .6rem;
  font-size: .92rem;
}
.finding h3 { margin: 0 0 .3rem; font-size: .98rem; }
.finding p { margin: .25rem 0; }
.remediation { color: #1f6d43; }
.qualifications, .confidence, .evidence { color: #5b6b7d; font-size: .85rem; }
.diagnose {
  display: inline-block; margin: .5rem 0 0; padding: .3rem .8rem; font-size: .85rem;
  border: 1px solid #1f6feb; border-radius: 6px; color: #1f6feb; text-decoration: none;
}
.diagnose:hover { background: #1f6feb; color: white; }\
"""
