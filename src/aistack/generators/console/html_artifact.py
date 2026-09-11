from __future__ import annotations

from pathlib import Path

from aistack.contracts.console_link import ConsoleLink
from aistack.generators.history import write_artifact_with_history
from aistack.renderers.console.html import render_html


class ConsoleHtmlArtifactGenerator:
    """
    Generate the `console.html` artifact from the owner's declared
    `ConsoleLink`s.

    Mirrors `HealthHtmlArtifactGenerator`/
    `ArchitectureHtmlArtifactGenerator` exactly: Observation History
    (`write_artifact_with_history`) applies here the same way it
    applies to every other generated artifact this heritage writes —
    a rendered console is as disposable and as worth keeping every
    run of as `architecture.html`/`health.html` are.

    Takes an already-loaded tuple of `ConsoleLink`s —
    `aistack.cli.console_render` is where `console_links.yml` is
    loaded — the same "this class is only the I/O step" split every
    other generator in this package already holds.
    """

    def generate(self, links: tuple[ConsoleLink, ...], output_path: Path) -> Path:
        content = render_html(links)
        write_artifact_with_history(content, output_path)

        return output_path
