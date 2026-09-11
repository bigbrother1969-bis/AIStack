from __future__ import annotations

from aistack.contracts.health_score import (
    ACTION_REQUIRED,
    EXCELLENT,
    TO_WATCH,
    HealthScore,
)
from aistack.contracts.runtime_finding import CitedReading, MatchedLine, RuntimeFinding
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.renderers.text import escape_text

_BUCKET_BADGE_CLASS = {
    EXCELLENT: "badge-clean",
    TO_WATCH: "badge-watch",
    ACTION_REQUIRED: "badge-alert",
}


def render_html(
    cockpit: HealthCockpit,
    score: HealthScore | None = None,
    score_note: str = "",
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

    **No client-side script, unlike `architecture.html`.** That page
    renders a Mermaid diagram, which needs a browser to draw; a
    domain's findings are already text — `interpretation`,
    `remediation`, the evidence count — so this page is server-side
    HTML only, plain text on load, nothing to fail to execute.

    Pure — no wall clock, the same discipline `render_html` for
    architecture already holds: the same cockpit and score always
    render to byte-identical output, so `HealthHtmlArtifactGenerator`
    (`aistack/generators/health/html_artifact.py`) is what stamps
    *when* a copy was produced, via `write_artifact_with_history`, not
    this function.
    """

    domain_count = len(cockpit.domains)
    instrumented_count = sum(1 for domain in cockpit.domains if domain.instrumented)

    sections = "\n".join(_render_domain(domain) for domain in cockpit.domains)

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>AIStack — Cockpit Santé</title>
<style>
{_STYLE}
</style>
</head>
<body>
<header>
  <h1>Cockpit santé — AIStack</h1>
  <p class="meta">
    {instrumented_count} / {domain_count} domaine(s) instrumenté(s)
  </p>
  {_render_score(score, score_note)}
</header>

{sections}
</body>
</html>
"""


def _render_score(score: HealthScore | None, score_note: str) -> str:
    if score is not None:
        badge_class = _BUCKET_BADGE_CLASS[score.bucket]

        return (
            f'<p class="score">Score de santé : '
            f"<strong>{score.value}/100</strong> "
            f'<span class="badge {badge_class}">{escape_text(score.bucket)}</span> '
            f"— {score.measured_domains}/{score.total_domains} domaine(s) mesuré(s)"
            f"</p>"
        )

    if score_note:
        return (
            f'<p class="score score-unavailable">'
            f"Score de santé : non calculé — {escape_text(score_note)}"
            f"</p>"
        )

    return ""


def _render_domain(domain: HealthDomain) -> str:
    if not domain.instrumented:
        return f"""<section class="domain domain-not-instrumented">
  <h2>{escape_text(domain.name)} <span class="badge badge-not-instrumented">non instrumenté</span></h2>
  <p class="note">{escape_text(domain.note)}</p>
</section>"""

    if not domain.findings:
        return f"""<section class="domain domain-clean">
  <h2>{escape_text(domain.name)} <span class="badge badge-clean">rien à signaler</span></h2>
</section>"""

    findings = "\n".join(_render_finding(finding) for finding in domain.findings)

    return f"""<section class="domain domain-alert">
  <h2>{escape_text(domain.name)} <span class="badge badge-alert">{len(domain.findings)} finding(s)</span></h2>
  {findings}
</section>"""


def _render_finding(finding: RuntimeFinding) -> str:
    qualifications = (
        f"<p class=\"qualifications\">qualifications : "
        f"{escape_text(', '.join(finding.qualifications))}</p>"
        if finding.qualifications
        else ""
    )

    return f"""  <article class="finding">
    <h3>{escape_text(finding.subject)} — {escape_text(finding.signature)}</h3>
    <p class="interpretation">{escape_text(finding.interpretation)}</p>
    <p class="remediation">→ {escape_text(finding.remediation)}</p>
    <p class="confidence">confiance : {escape_text(finding.confidence)} —
      fondement : {escape_text(finding.grounding)}</p>
    {qualifications}
    <p class="evidence">{_evidence_summary(finding.evidence)}</p>
  </article>"""


def _evidence_summary(evidence: tuple[MatchedLine | CitedReading, ...]) -> str:
    readings = [item for item in evidence if isinstance(item, CitedReading)]
    lines = [item for item in evidence if isinstance(item, MatchedLine)]

    parts = []
    if readings:
        parts.append(
            f"{len(readings)} lecture(s) citée(s) : "
            + escape_text(
                ", ".join(f"{item.provider} → {item.reading!r}" for item in readings)
            )
        )
    if lines:
        parts.append(f"{len(lines)} ligne(s) de log citée(s)")

    return " — ".join(parts) if parts else f"{len(evidence)} élément(s) de preuve"


_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: sans-serif; max-width: 900px; margin: 2rem auto;
  color: #1f2933; padding: 0 1rem;
}
header { margin-bottom: 1.4rem; }
.meta { color: #666; font-size: .85rem; }
.domain {
  border: 1px solid #ddd; border-radius: 8px; padding: 1rem 1.2rem;
  margin-bottom: 1rem;
}
.domain h2 { margin: 0 0 .4rem; font-size: 1.1rem; display: flex; align-items: center; gap: .6rem; }
.badge {
  font-size: .72rem; font-weight: normal; padding: .15rem .5rem;
  border-radius: 999px; border: 1px solid;
}
.badge-not-instrumented { background: #f0f0f0; border-color: #666; color: #444; }
.badge-clean { background: #dff6dd; border-color: #116329; color: #116329; }
.badge-watch { background: #fff4d6; border-color: #8a6100; color: #8a6100; }
.badge-alert { background: #fde2e1; border-color: #b00020; color: #b00020; }
.domain-not-instrumented { background: #fafafa; }
.domain-clean { background: #f7fdf6; }
.domain-alert { background: #fff8f8; }
.note { color: #555; font-size: .9rem; }
.score { font-size: .95rem; margin: .4rem 0 0; }
.score-unavailable { color: #666; }
.finding {
  border-top: 1px solid #eee; padding-top: .6rem; margin-top: .6rem;
  font-size: .92rem;
}
.finding h3 { margin: 0 0 .3rem; font-size: .98rem; }
.finding p { margin: .25rem 0; }
.remediation { color: #116329; }
.qualifications, .confidence, .evidence { color: #555; font-size: .85rem; }\
"""
