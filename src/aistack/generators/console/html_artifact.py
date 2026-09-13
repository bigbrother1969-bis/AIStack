from __future__ import annotations

from pathlib import Path

from aistack.contracts.console_link import ConsoleLink
from aistack.contracts.health_score import HealthScore
from aistack.generators.history import write_artifact_with_history
from aistack.health.cockpit import HealthCockpit
from aistack.renderers.console.html import render_html


class ConsoleHtmlArtifactGenerator:
    """
    Generate the `console.html` artifact from the owner's declared
    `ConsoleLink`s and, since 2026-09-13, a `HealthCockpit` snapshot
    for the health cartouche
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` § 11.9).

    Mirrors `HealthHtmlArtifactGenerator`/
    `ArchitectureHtmlArtifactGenerator` exactly: Observation History
    (`write_artifact_with_history`) applies here the same way it
    applies to every other generated artifact this heritage writes —
    a rendered console is as disposable and as worth keeping every
    run of as `architecture.html`/`health.html` are.

    Takes an already-loaded tuple of `ConsoleLink`s —
    `aistack.cli.console_render` is where `console_links.yml` is
    loaded — the same "this class is only the I/O step" split every
    other generator in this package already holds. `cockpit`/`score`/
    `score_note` default to the pre-cartouche shape (`None`, `None`,
    `""`) so a caller with nothing to summarize renders exactly as it
    always has — the same optional-parameter idiom `HealthHtml
    ArtifactGenerator.generate` already holds for `score`/`score_note`.
    """

    def generate(
        self,
        links: tuple[ConsoleLink, ...],
        output_path: Path,
        cockpit: HealthCockpit | None = None,
        score: HealthScore | None = None,
        score_note: str = "",
    ) -> Path:
        content = render_html(links, cockpit=cockpit, score=score, score_note=score_note)
        write_artifact_with_history(content, output_path)

        return output_path
