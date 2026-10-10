from __future__ import annotations

from pathlib import Path

from aistack.contracts.console_link import ConsoleLink
from aistack.contracts.health_score import HealthScore
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.generators.history import write_artifact_with_history
from aistack.health.cockpit import HealthCockpit
from aistack.console.identity import ConsoleIdentity
from aistack.__main__ import declared_version
from aistack.renderers.console.html import render_html


class ConsoleHtmlArtifactGenerator:
    """
    Generate the `console.html` artifact, with Observation History,
    from the declared `ConsoleLink`s and an optional `HealthCockpit`
    snapshot for the health cartouche.

    This class is only the I/O step: `aistack.cli.console_render` loads
    `console_links.yml`. Without `cockpit`, `score` or
    `technical_debt_score` the matching part is left out. `lang`
    (ADR-0010) is the page language, the reference when `None`.
    `version` is shown under the lockup; when `None`, the installed
    distribution's (`aistack.__main__.declared_version`).
    """

    def generate(
        self,
        links: tuple[ConsoleLink, ...],
        output_path: Path,
        cockpit: HealthCockpit | None = None,
        score: HealthScore | None = None,
        score_note: str = "",
        technical_debt_score: TechnicalDebtScore | None = None,
        technical_debt_note: str = "",
        lang: str | None = None,
        identity: ConsoleIdentity | None = None,
        version: str | None = None,
    ) -> Path:
        content = render_html(
            links,
            cockpit=cockpit,
            score=score,
            score_note=score_note,
            technical_debt_score=technical_debt_score,
            technical_debt_note=technical_debt_note,
            lang=lang,
            identity=identity,
            version=declared_version() if version is None else version,
        )
        write_artifact_with_history(content, output_path)

        return output_path
