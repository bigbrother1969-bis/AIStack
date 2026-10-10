from __future__ import annotations

from pathlib import Path

from aistack.architecture.beszel_reading import BeszelSystemReading
from aistack.architecture.dependency_graph import DependencyGraph
from aistack.architecture.http_probe_reading import HttpProbeReading
from aistack.architecture.topology_definition import InfrastructureTopologyDefinition
from aistack.architecture.views import ArchitectureView
from aistack.generators.history import write_artifact_with_history
from aistack.renderers.architecture.html import render_html


class ArchitectureHtmlArtifactGenerator:
    """
    Generate the `architecture.html` artifact, with Observation
    History, from already-built views (`build_all_views(graph)`).

    This class is only the I/O step: `topology`, `beszel_readings`,
    `dependency_graph` and `cmdb_readings` are loaded or built by the
    CLI and passed straight through to `render_html`.
    """

    def generate(
        self,
        views: tuple[ArchitectureView, ...],
        output_path: Path,
        topology: InfrastructureTopologyDefinition | None = None,
        beszel_readings: tuple[BeszelSystemReading, ...] = (),
        dependency_graph: DependencyGraph | None = None,
        cmdb_readings: tuple[HttpProbeReading, ...] = (),
        lang: str | None = None,
    ) -> Path:
        # `lang` (ADR-0010): the page language, the reference when `None`.
        content = render_html(
            views,
            topology,
            beszel_readings,
            dependency_graph,
            cmdb_readings,
            lang=lang,
        )
        write_artifact_with_history(content, output_path)

        return output_path
