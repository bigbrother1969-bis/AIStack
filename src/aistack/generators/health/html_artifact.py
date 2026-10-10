from __future__ import annotations

from pathlib import Path

from aistack.contracts.health_score import HealthScore
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.generators.history import write_artifact_with_history
from aistack.health.cockpit import HealthCockpit
from aistack.renderers.health.html import render_html


class HealthHtmlArtifactGenerator:
    """
    Generate the `health.html` artifact, with Observation History,
    from an already-built `HealthCockpit` and optional scores.

    This class is only the I/O step: `aistack.cli.health_render` builds
    the cockpit and `aistack.health.score.compute_health_score` the
    score (`OPS-0008`). Without `score` or `technical_debt_score` the
    matching card is left out. `lang` (ADR-0010) is the page language,
    the reference when `None`. `troubleshooting_base_url`, when given,
    adds a "Diagnostiquer" button to each finding.
    """

    def generate(
        self,
        cockpit: HealthCockpit,
        output_path: Path,
        score: HealthScore | None = None,
        score_note: str = "",
        technical_debt_score: TechnicalDebtScore | None = None,
        technical_debt_note: str = "",
        lang: str | None = None,
        troubleshooting_base_url: str | None = None,
    ) -> Path:
        content = render_html(
            cockpit,
            score=score,
            score_note=score_note,
            technical_debt_score=technical_debt_score,
            technical_debt_note=technical_debt_note,
            lang=lang,
            troubleshooting_base_url=troubleshooting_base_url,
        )
        write_artifact_with_history(content, output_path)

        return output_path
