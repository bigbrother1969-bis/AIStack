from __future__ import annotations

import socket
from pathlib import Path

from aistack.ai_runtime.policy import current_policy
from aistack.config import configured
from aistack.console.identity import load_console_identity
from aistack.console.yaml import load_console_links_yaml
from aistack.generators.console import ConsoleHtmlArtifactGenerator
from aistack.generators.history import ensure_link, write_view
from aistack.health import domains
from aistack.health.domains import build_cockpit
from aistack.health.score import compute_health_score
from aistack.health.score_weights import health_score_weights
from aistack.health.technical_debt import technical_debt_score
from aistack.i18n import default_languages
from aistack.i18n.pages import page_file
from aistack.instance.yaml import load_instance_config_yaml
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.kernel.registries.provider_registry import ProviderRegistry

SHIPPED_CONSOLE_LINKS = Path(__file__).resolve().parents[1] / "console" / "definitions" / "console_links.yml"
DEFAULT_CONSOLE_LINKS = configured(SHIPPED_CONSOLE_LINKS)

DEFAULT_GENERATED_DIR = "reports/generated"

# The generated pages exposed in the public directory; other console
# links are separate services reached by their own URL.
_SERVED_ARTIFACTS = ("console.html", "architecture.html", "health.html")

_INDEX_HTML = """\
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=console.html">
<title>AIStack — Console</title>
</head>
<body>
<p>AIStack — <a href="console.html">ouvrir la console</a>.</p>
</body>
</html>
"""


class ConsoleRenderTask:
    """
    Render the console page with its health and technical-debt scores
    (`console.render`, ADR-0027 § 10).

    The third chain the Runtime executes. The cockpit and the scores
    (OPS-0008 weights, as in `health.render`) are computed once from the
    providers the Kernel registered, then the page is written once per
    declared language (ADR-0010 § 5): the reference keeps `console.html`,
    the others get `console.<code>.html`. Missing weights render as a
    note, not an omission.

    `console.html` is written beside `architecture.html` and
    `health.html`, not inside the public directory: each artifact gets a
    `history/` sibling that must never be reachable over HTTP. The
    public directory only links the pages, with relative symlinks, and
    holds an index; serving is `aistack.web.server`'s job (ADR-0012).

    The request payload's `generated_dir` (default
    `DEFAULT_GENERATED_DIR`) says where everything is written.

    Returns an Observation of plain values: the page, the languages
    written, how many links it holds and where it is served from.
    """

    task_id = "console.render"
    task_name = "Console"

    def __init__(self, providers: ProviderRegistry) -> None:
        self._providers = providers

    def execute(self, request: Request) -> Observation:
        generated_dir = Path(request.payload.get("generated_dir", DEFAULT_GENERATED_DIR))
        public_dir = generated_dir / "public"
        languages = default_languages()

        cockpit = build_cockpit(socket.gethostname(), self._providers)
        weights, score_note = health_score_weights(domains.SOURCES.score_weights)
        score = compute_health_score(cockpit, weights) if weights is not None else None
        debt_score, debt_score_note = technical_debt_score(cockpit, weights)

        written: list[str] = []
        links_count = 0
        instance = load_instance_config_yaml(domains.SOURCES.instance_config)
        policy = current_policy()

        for language in languages.available:
            links = load_console_links_yaml(
                DEFAULT_CONSOLE_LINKS,
                lang=language.code,
                languages=languages,
                instance=instance,
                completing=SHIPPED_CONSOLE_LINKS,
                policy=policy,
            )
            links_count = len(links)
            output_path = page_file(
                generated_dir, "console.html", language.code, languages.reference
            )

            ConsoleHtmlArtifactGenerator().generate(
                links=links,
                output_path=output_path,
                cockpit=cockpit,
                score=score,
                score_note=score_note,
                technical_debt_score=debt_score,
                technical_debt_note=debt_score_note,
                lang=language.code,
                identity=load_console_identity(lang=language.code, languages=languages),
            )
            written.append(output_path.name)

        public_dir.mkdir(parents=True, exist_ok=True)

        for name in _SERVED_ARTIFACTS:
            ensure_link(public_dir / name, Path("..") / name)

        write_view(_INDEX_HTML, public_dir / "index.html")

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={
                "output_path": str(generated_dir / "console.html"),
                "pages": written,
                "links": links_count,
                "served_from": str(generated_dir),
            },
        )
