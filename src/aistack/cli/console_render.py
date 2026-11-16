from __future__ import annotations

from aistack.config import configured

import socket
from pathlib import Path

from aistack.console.identity import load_console_identity
from aistack.console.yaml import load_console_links_yaml
from aistack.generators.console import ConsoleHtmlArtifactGenerator
from aistack.health import domains
from aistack.health.domains import build_cockpit
from aistack.health.score import compute_health_score
from aistack.health.score_weights import health_score_weights
from aistack.health.technical_debt import technical_debt_score
from aistack.i18n import default_languages
from aistack.i18n.pages import page_file
from aistack.instance.yaml import load_instance_config_yaml
from aistack.kernel.bootstrap import registered_providers

DEFAULT_CONSOLE_LINKS = (
    configured(Path(__file__).resolve().parents[1]
    / "console"
    / "definitions"
    / "console_links.yml")
)


# `console.html` is written beside `architecture.html` and `health.html`,
# not inside `PUBLIC_DIR`: each artifact gets a `history/` sibling that
# must never be reachable over HTTP. `PUBLIC_DIR` only links the pages.
GENERATED_DIR = Path("reports/generated")
PUBLIC_DIR = GENERATED_DIR / "public"

# The generated pages exposed in `PUBLIC_DIR`; other console links are
# separate services reached by their own URL.
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


def main() -> None:
    """
    Render the console page with its health and technical-debt scores.

    The cockpit and scores (OPS-0008 weights, as in `health_render`) are
    computed once, then the page is written once per declared language
    (ADR-0010 § 5): the reference keeps `console.html`, others get
    `console.<code>.html`. Missing weights render as a note, not an
    omission. Serving is `aistack.web.server`'s job (ADR-0012);
    `PUBLIC_DIR` keeps relative symlinks to the reference pages for a
    plain static-file fallback.
    """

    languages = default_languages()

    # The entry point boots the Kernel and hands its providers to the
    # cockpit, which reads through them (ADR-0027 § 9).
    cockpit = build_cockpit(socket.gethostname(), registered_providers())
    weights, score_note = health_score_weights(domains.SOURCES.score_weights)
    score = compute_health_score(cockpit, weights) if weights is not None else None
    debt_score, debt_score_note = technical_debt_score(cockpit, weights)

    written: list[str] = []
    links_count = 0
    instance = load_instance_config_yaml(domains.SOURCES.instance_config)

    for language in languages.available:
        links = load_console_links_yaml(
            DEFAULT_CONSOLE_LINKS,
            lang=language.code,
            languages=languages,
            instance=instance,
        )
        links_count = len(links)
        output_path = page_file(
            GENERATED_DIR, "console.html", language.code, languages.reference
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

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    for name in _SERVED_ARTIFACTS:
        _ensure_public_symlink(PUBLIC_DIR / name, Path("..") / name)

    (PUBLIC_DIR / "index.html").write_text(_INDEX_HTML, encoding="utf-8")

    print(
        f"Console written to {GENERATED_DIR / 'console.html'} "
        f"({links_count} link(s); {', '.join(written)}); served from "
        f"{GENERATED_DIR} by aistack.web.server"
    )


def _ensure_public_symlink(link_path: Path, target: Path) -> None:
    """
    Make `link_path` a relative symlink to `target`; idempotent.

    A real file there was put by hand, so it raises rather than overwrite it.
    """

    if link_path.is_symlink():
        if link_path.readlink() == target:
            return
        link_path.unlink()
    elif link_path.exists():
        raise ValueError(
            f"{link_path} already exists and is not a symlink this "
            f"command manages; remove it by hand before running "
            f"console_render again"
        )

    link_path.symlink_to(target)


if __name__ == "__main__":
    main()
