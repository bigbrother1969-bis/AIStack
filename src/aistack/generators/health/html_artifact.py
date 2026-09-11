from __future__ import annotations

from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.health.cockpit import HealthCockpit
from aistack.renderers.health.html import render_html


class HealthHtmlArtifactGenerator:
    """
    Generate the `health.html` artifact from a `HealthCockpit`
    snapshot.

    Mirrors `ArchitectureHtmlArtifactGenerator` exactly: Observation
    History (`write_artifact_with_history`) applies here the same way
    it applies to every other generated artifact this heritage
    writes — a rendered cockpit is as disposable and as worth keeping
    every run of as `architecture.html` is.

    Takes an already-built `HealthCockpit` — `aistack.cli
    .health_render` is where each domain gets constructed — the same
    "this class is only the I/O step" split every other generator in
    this package already holds.
    """

    def generate(self, cockpit: HealthCockpit, output_path: Path) -> Path:
        content = render_html(cockpit)
        write_artifact_with_history(content, output_path)

        return output_path
