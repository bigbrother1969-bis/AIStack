from __future__ import annotations

from datetime import date
from urllib.parse import quote

from aistack.contracts.health_score import (
    ACTION_REQUIRED,
    EXCELLENT,
    TO_WATCH,
    HealthScore,
)
from aistack.contracts.quarantine_reading import READY, USED, QuarantineReading
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
    quarantine: tuple[QuarantineReading, ...] = (),
    quarantine_note: str = "",
) -> str:
    """
    Wrap a `HealthCockpit` snapshot into one self-contained HTML
    page — `PLAN-J7`'s cockpit visuel
    (`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` § 6.4/6.5), the
    second tenant of the `renderers/` package after
    `aistack.renderers.architecture`.

    **A score, once four domains gave it something to weigh against**
    (`OPS-0008`, decided 2026-09-11): `score` is
    `aistack.health.score.compute_health_score`'s own result, computed
    by this function's caller from `OPS-0008`'s declared weights —
    this function only displays it, never derives it, the same split
    `_render_domain` already holds for a `RuntimeFinding` it did not
    qualify itself. `score=None` with a non-empty `score_note` renders
    the same honest absence a not-instrumented domain already does
    (`FDN-0003` Article 12: weights that failed to load are named, not
    silently dropped); `score=None` with an empty note (every existing
    call this function had before `OPS-0008` existed) renders no score
    section at all, keeping every prior domain-only test unaffected.

    **A dedicated "Dette technique" card, added 2026-09-23**
    (`PLAN-J11` § 11.9.1) — `technical_debt_score` is
    `aistack.health.technical_debt.compute_technical_debt_score`'s own
    result, rendered right after the score paragraph above, the
    placement the owner named ("juste après le score santé global")
    when this card was scoped, never folded into a per-domain section:
    `OPS-0004/technical-debt` cuts across domains, this card does too.
    Same optional-parameter, same two-branch idiom `score`/
    `score_note` already holds: `None` with a note is an honest
    absence, `None` with no note renders nothing, keeping every call
    from before this card existed unaffected.

    **No client-side script, unlike `architecture.html`.** That page
    renders a Mermaid diagram, which needs a browser to draw; a
    domain's findings are already text — `interpretation`,
    `remediation`, the evidence count — so this page is server-side
    HTML only, plain text on load, nothing to fail to execute.

    **`quarantine`, added 2026-10-05** (`OPS-0012`) — the quarantined
    code the card's score already counts, as one line under it: how
    many items, until when, how many uses recorded, and each item used
    or ready to be deleted by name. Empty (every earlier call) renders
    no line; `quarantine_note` names a register that could not be read.

    Pure — no wall clock, the same discipline `render_html` for
    architecture already holds: the same cockpit and score always
    render to byte-identical output, so `HealthHtmlArtifactGenerator`
    (`aistack/generators/health/html_artifact.py`) is what stamps
    *when* a copy was produced, via `write_artifact_with_history`, not
    this function.

    **Viewport meta and favicon, added 2026-09-30**
    (`claude/AUDIT-CONSOLE-ARCHITECTURE-HEALTH-2026-09-29.md`, constats
    1/3) — this page had neither. `MARK_DATA_URI` comes from
    `aistack.renderers.assets`, the same vendored mark `console.html`
    already shows.

    **`troubleshooting_base_url`, added 2026-09-30** (the owner,
    reading this page's own real findings: "les findings en rouge
    doivent être cliquables et doivent diriger vers... la possibilité
    de résoudre le problème de façon accompagnée par les modules
    d'IA"). `None` (every call this function had before this
    feature existed) renders every finding exactly as before — no
    "Diagnostiquer" button — the same "absent parameter changes
    nothing" idiom `score`/`technical_debt_score` already hold. A
    real base URL (`aistack.cli.health_render.main` resolves it via
    `service_url("web_lan")` plus `/troubleshooting` since 2026-10-03, the R10 pattern
    `console_render.py` already uses for its own links) adds one
    small `<form method="post" action="{base_url}/finding/{key}
    /start">` per finding, pointing at that LAN-only assistant —
    still pure: the base URL is handed in, never looked up here.

    **The routing `key` a finding's button submits to is not always
    `finding.subject`** — the same collision-safe composite key
    `aistack.troubleshooting.findings.QualifiedFinding` computes for
    its own routing (see that module's docstring for the full
    reasoning and the confirmed real collision — "gigabyte",
    "nextcloud", "immich" each named today by both Tests PRA and État
    persistant), computed independently here from `cockpit.domains`
    alone since this renderer never imports that FastAPI app (`aistack
    .renderers` imports nothing outside itself and the packages it
    already depended on). **A known, accepted narrowing**: this
    renderer's own collision set only spans `cockpit.domains` — the
    assistant's own CPU/consumption check (`CONSUMPTION_DOMAIN`, never
    part of `HealthCockpit`) is outside what this pure function can
    see, so a finding whose subject *also* happens to be flagged for
    CPU consumption right now could, in the rare case, submit to a key
    the assistant resolves differently. That failure mode is a plain
    "not found, start again from the list" redirect at the
    assistant — never a wrong write, never a silently mismatched
    finding — so it is accepted rather than solved by duplicating the
    CPU-consumption check a fourth time into this renderer, a scope
    this feature was never cadred to take on.
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

{_render_technical_debt(technical_debt_score, technical_debt_note, t, _render_quarantine(quarantine, quarantine_note, t))}
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
            f'<span class="badge {badge_class}">'
            f"{escape_text(bucket_label(t, score.bucket))}</span> "
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
    score: TechnicalDebtScore | None, note: str, t: Translator, quarantine: str = ""
) -> str:
    heading = escape_text(t("health.page.technical_debt"))

    if score is not None:
        badge_class = _BUCKET_BADGE_CLASS[score.bucket]
        findings = t("health.page.technical_debt_findings", count=len(score.findings))

        return f"""<section class="technical-debt">
  <h2>{heading} <span class="badge {badge_class}">{escape_text(bucket_label(t, score.bucket))}</span></h2>
  <p class="score">
    <strong>{score.value}/100</strong> — {escape_text(findings)}
    {escape_text("OPS-0004/technical-debt")}
  </p>
{quarantine}</section>"""

    if note:
        unavailable = t("health.page.technical_debt_unavailable", note=note)

        return f"""<section class="technical-debt technical-debt-unavailable">
  <h2>{heading}</h2>
  <p class="note score-unavailable">{escape_text(unavailable)}</p>
{quarantine}</section>"""

    return ""


def _day(value: date, t: Translator) -> str:
    return value.strftime("%d/%m/%Y") if t.lang == "fr" else value.isoformat()


def _render_quarantine(
    readings: tuple[QuarantineReading, ...], note: str, t: Translator
) -> str:
    """The quarantine's line in the technical-debt card (`OPS-0012`)."""

    if note:
        return f'  <p class="quarantine note">{escape_text(t("health.page.quarantine_unavailable", note=note))}</p>\n'
    if not readings:
        return ""
    uses = sum(reading.uses for reading in readings)
    review = min(reading.review_after for reading in readings)
    summary = t(
        "health.page.quarantine",
        count=len(readings),
        review=_day(review, t),
        uses=uses,
    )
    items = []
    for reading in readings:
        if reading.state == USED:
            text = t("health.page.quarantine_used", entry=reading.entry, paths=", ".join(reading.paths), uses=reading.uses, last=reading.last_use)
            items.append(f'    <li class="quarantine-used">{escape_text(text)}</li>')
        elif reading.state == READY:
            text = t("health.page.quarantine_ready", entry=reading.entry, paths=", ".join(reading.paths))
            items.append(f'    <li class="quarantine-ready">{escape_text(text)}</li>')
    listed = f'  <ul class="quarantine-items">\n{chr(10).join(items)}\n  </ul>\n' if items else ""
    return (
        f'  <p class="quarantine">{escape_text(summary)} '
        f'{escape_text("OPS-0012")}</p>\n{listed}'
    )


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
    """
    Only the labels around a finding are translated (ADR-0010 § 4): its
    subject, signature, interpretation, remediation, confidence and
    grounding are shown exactly as the runtime qualified them.
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
        # administrator's action of the Troubleshooting screen itself,
        # on the LAN listener, with that screen's own session and token.
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


# Same charte graphique retouch as `aistack.renderers.console.html`
# (2026-09-26, see that module's own comment for the full rationale
# and where each value comes from) — identical across the three
# static pages by design, not by shared code. The `.domain-*`/
# `.badge-*` state tints keep their meaning, only lightly retinted.
# Width, same reasoning and same value as that module's own comment
# (ADR-0011 §26, 2026-09-29): `min(96vw, 1600px)`, not a fixed 900px.
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
.technical-debt .quarantine { margin: .4rem 0 0; font-size: .9rem; color: #444; }
.quarantine-items { margin: .3rem 0 0; padding-left: 1.2rem; font-size: .9rem; }
.quarantine-used { color: #b42318; font-weight: 600; }
.quarantine-ready { color: #7d4e00; }
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
