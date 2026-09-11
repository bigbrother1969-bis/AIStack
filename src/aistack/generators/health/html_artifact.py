from __future__ import annotations

from pathlib import Path

from aistack.contracts.health_score import HealthScore
from aistack.generators.history import write_artifact_with_history
from aistack.health.cockpit import HealthCockpit
from aistack.renderers.health.html import render_html


class HealthHtmlArtifactGenerator:
    """
    Generate the `health.html` artifact from a `HealthCockpit`
    snapshot and, once `OPS-0008`'s weights are available, its
    `HealthScore`.

    Mirrors `ArchitectureHtmlArtifactGenerator` exactly: Observation
    History (`write_artifact_with_history`) applies here the same way
    it applies to every other generated artifact this heritage
    writes — a rendered cockpit is as disposable and as worth keeping
    every run of as `architecture.html` is.

    Takes an already-built `HealthCockpit` and an already-computed
    `HealthScore` — `aistack.cli.health_render` is where each domain
    is constructed and `aistack.health.score.compute_health_score` is
    where the score is derived from it — the same "this class is only
    the I/O step" split every other generator in this package already
    holds. `score`/`score_note` default to the pre-`OPS-0008` shape
    (no score, no note) so a caller with nothing to weigh yet renders
    exactly as it always has.
    """

    def generate(
        self,
        cockpit: HealthCockpit,
        output_path: Path,
        score: HealthScore | None = None,
        score_note: str = "",
    ) -> Path:
        content = render_html(cockpit, score=score, score_note=score_note)
        write_artifact_with_history(content, output_path)

        return output_path
