from __future__ import annotations

from pathlib import Path

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
    """

    def generate(
        self, views: tuple[ArchitectureView, ...], output_path: Path
    ) -> Path:
        content = render_html(views)
        write_artifact_with_history(content, output_path)

        return output_path
