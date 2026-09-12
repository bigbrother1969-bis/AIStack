from __future__ import annotations

from pathlib import Path

from aistack.architecture.beszel_reading import BeszelSystemReading
from aistack.architecture.dependency_graph import DependencyGraph
from aistack.architecture.topology_definition import InfrastructureTopologyDefinition
from aistack.architecture.views import ArchitectureView
from aistack.generators.history import write_artifact_with_history
from aistack.renderers.architecture.html import render_html


class ArchitectureHtmlArtifactGenerator:
    """
    Generate the `architecture.html` artifact from a graph's views.

    **Keeps Observation History, same as every other CLI generator**
    (`write_artifact_with_history`) — a rendered page is as much a
    generated artifact as the JSON catalogs the other four generators
    write, and the same defect they were fixed for (a plain
    `write_text` destroying the previous run) applies here just as
    much.

    Takes already-built `views` — `build_all_views(graph)`'s own
    output — rather than a bare `ArchitectureGraph`, the same way
    `ComposeCatalogArtifactGenerator.generate` takes an already-built
    `Catalog`: this class is only the I/O step, not where the domain
    object gets constructed.

    `topology` (added 2026-09-12, §10) is optional and passed straight
    through to `render_html` — this class does not load
    `infrastructure_topology.yml` itself, the same way it does not
    load `service_categorization.yml` itself; the CLI is where both
    reads happen. `beszel_readings` (same day, §10 last bullet) is the
    same story one layer further: this class never calls
    `BeszelProvider` itself, it only carries the already-built
    readings through. `dependency_graph` (same day, §10 third gap) is
    the same story again: this class never calls
    `build_dependency_graph` itself, it only carries the already-built
    graph through.
    """

    def generate(
        self,
        views: tuple[ArchitectureView, ...],
        output_path: Path,
        topology: InfrastructureTopologyDefinition | None = None,
        beszel_readings: tuple[BeszelSystemReading, ...] = (),
        dependency_graph: DependencyGraph | None = None,
    ) -> Path:
        content = render_html(views, topology, beszel_readings, dependency_graph)
        write_artifact_with_history(content, output_path)

        return output_path
