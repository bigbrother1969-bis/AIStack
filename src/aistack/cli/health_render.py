from __future__ import annotations

import socket
from pathlib import Path

from aistack.contracts.health_score import HealthScore, HealthScoreWeights
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.generators.health import HealthHtmlArtifactGenerator
from aistack.health import domains
from aistack.health.cockpit import HealthCockpit
from aistack.health.domains import build_cockpit
from aistack.health.score import compute_health_score
from aistack.health.score_weights import health_score_weights
from aistack.health.plan import debt_plan, health_plan
from aistack.health.technical_debt import technical_debt_score
from aistack.i18n import Languages, default_languages
from aistack.i18n.pages import page_file
from aistack.instance.yaml import load_instance_config_yaml
from aistack.kernel.bootstrap import registered_providers
from aistack.renderers.plan.html import PLAN_PAGE, render_plan
from aistack.vigil.snapshot import take as take_snapshot, write as write_snapshot

# The assistant's prefix on the web application's LAN listener
# (ADR-0012, `aistack.web.troubleshooting.PREFIX`).
TROUBLESHOOTING_PATH = "/troubleshooting"


def main() -> None:
    """
    Render the health cockpit, its scores, the action plan and the vigil snapshot.

    The health and technical-debt scores share one cockpit and one load
    of the OPS-0008 weights. Each finding links to the Troubleshooting
    Assistant when the instance config gives its address.
    """

    # The entry point boots the Kernel and hands its providers to the
    # cockpit, which reads through them (ADR-0027 § 9).
    cockpit = build_cockpit(socket.gethostname(), registered_providers())

    weights, score_note = health_score_weights(domains.SOURCES.score_weights)
    score = compute_health_score(cockpit, weights) if weights is not None else None
    debt_score, debt_score_note = technical_debt_score(cockpit, weights)

    try:
        troubleshooting_base_url: str | None = (
            load_instance_config_yaml(domains.SOURCES.instance_config).service_url("web_lan")
            + TROUBLESHOOTING_PATH
        )
    except (ValueError, OSError):
        # Optional: without it, findings get no "Diagnostiquer" button.
        troubleshooting_base_url = None

    # ADR-0010 § 5: one page per declared language from the same cockpit;
    # the reference language keeps `health.html`.
    languages = default_languages()
    generated_dir = Path("reports/generated")
    output_path = generated_dir / "health.html"

    for language in languages.available:
        written = HealthHtmlArtifactGenerator().generate(
            cockpit=cockpit,
            output_path=page_file(
                generated_dir, "health.html", language.code, languages.reference
            ),
            score=score,
            score_note=score_note,
            technical_debt_score=debt_score,
            technical_debt_note=debt_score_note,
            lang=language.code,
            troubleshooting_base_url=troubleshooting_base_url,
        )

        if language.code == languages.reference:
            output_path = written

    # The vigil compares this render with the one before.
    write_snapshot(
        take_snapshot(
            cockpit,
            score.value if score is not None else None,
            debt_score.value if debt_score is not None else None,
        ),
        generated_dir,
    )

    plan_written = write_plan(
        cockpit,
        weights,
        score=score,
        score_note=score_note,
        debt_score=debt_score,
        debt_note=debt_score_note,
        troubleshooting_base_url=troubleshooting_base_url,
        generated_dir=generated_dir,
        languages=languages,
    )

    if score is not None:
        print(
            f"Health cockpit written to {output_path} "
            f"(score: {score.value}/100, {score.bucket}, "
            f"{score.measured_domains}/{score.total_domains} domain(s) measured)"
        )
    else:
        print(f"Health cockpit written to {output_path} (score: {score_note})")

    if debt_score is not None:
        print(
            f"Technical-debt score: {debt_score.value}/100, {debt_score.bucket}, "
            f"{len(debt_score.findings)} finding(s)"
        )
    else:
        print(f"Technical-debt score: {debt_score_note}")

    print(f"Action plan written to {plan_written}")


def write_plan(
    cockpit: HealthCockpit,
    weights: HealthScoreWeights | None,
    *,
    score: HealthScore | None,
    score_note: str,
    debt_score: TechnicalDebtScore | None,
    debt_note: str,
    troubleshooting_base_url: str | None,
    generated_dir: Path,
    languages: Languages,
) -> Path:
    """
    Write `plan.html`, the action plan the score badges open, once per language.

    Written plainly, not with `write_artifact_with_history`: it is a view
    of this run, not a history stream. Returns the reference-language path.
    """

    weight = (weights.for_domain("Services") or 0) if weights is not None else 0
    health = health_plan(cockpit, weights) if weights is not None else ()
    debt = debt_plan(cockpit, weight) if weights is not None else ()
    subject_counts: dict[str, int] = {}
    for domain in cockpit.domains:
        for finding in domain.findings:
            subject_counts[finding.subject] = subject_counts.get(finding.subject, 0) + 1

    reference = generated_dir / PLAN_PAGE
    for language in languages.available:
        path = page_file(generated_dir, PLAN_PAGE, language.code, languages.reference)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(
            render_plan(
                health,
                debt,
                score=score,
                score_note=score_note,
                debt_score=debt_score,
                debt_note=debt_note,
                weight=weight,
                subject_counts=subject_counts,
                troubleshooting_base_url=troubleshooting_base_url,
                lang=language.code,
                languages=languages,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
        if language.code == languages.reference:
            reference = path
    return reference


if __name__ == "__main__":
    main()
