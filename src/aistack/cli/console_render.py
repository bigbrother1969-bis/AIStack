from __future__ import annotations

from pathlib import Path

from aistack.console.yaml import load_console_links_yaml
from aistack.generators.console import ConsoleHtmlArtifactGenerator

# Same convention as `architecture_render.py`'s own
# `DEFAULT_CATEGORIZATION` — a `Path(__file__).resolve()`-relative
# default, not `importlib.resources`.
DEFAULT_CONSOLE_LINKS = (
    Path(__file__).resolve().parents[1]
    / "console"
    / "definitions"
    / "console_links.yml"
)

# `console.html` is generated the same way every other artifact in
# `reports/generated/` already is (`write_artifact_with_history`) —
# a plain sibling of `architecture.html`/`health.html`, not inside
# `PUBLIC_DIR` itself: `write_artifact_with_history` also writes a
# `history/<stem>/` subdirectory beside whatever it is handed, and
# that subdirectory must never be reachable over HTTP (`PLAN-J11`
# § 4 — the whole reason `PUBLIC_DIR` exists rather than serving
# `reports/generated/` directly is to keep this heritage's own
# internal diagnostics, `history/` included, off the LAN).
GENERATED_DIR = Path("reports/generated")
PUBLIC_DIR = GENERATED_DIR / "public"

# The three pages the console links to that this repository itself
# generates — `PLAN-J11` § 2's v1 scope narrowed to the two static
# ones. Selection UI and Priorité CPU are separate running services,
# reached directly (`console_links.yml`'s own `url`), not files this
# command serves.
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
    `PLAN-J11` § 2/§ 4: the console, generated the same way every
    other artifact this heritage produces is, then made reachable —
    the gap `PLAN-J11` § 4 named: nothing before this command ever
    served `reports/generated/` over HTTP at all, `architecture.html`
    and `health.html` included (both, until today, only ever read by
    SSHing into GIGABYTE and opening the file directly).

    **`PUBLIC_DIR` exposes three pages, not the whole directory.**
    `reports/generated/` also holds internal JSON catalogs (Docker
    Observation, Compose Catalog, Architecture Views) and each
    artifact's own `history/` — none of it meant for a browser.
    Relative symlinks (`_ensure_public_symlink`) keep `console.html`,
    `architecture.html` and `health.html` reachable from `PUBLIC_DIR`
    without copying them — a copy would drift stale the moment either
    of the other two commands regenerates its own file; a symlink
    cannot.

    **Serving `PUBLIC_DIR` itself is the owner's own next step, not
    this command's** — `deploy/systemd/aistack-console.service`
    (`PLAN-J11` § 4) runs a plain static file server against it, and
    pointing a reverse-proxy Host at that server is a manual Nginx
    Proxy Manager step this codebase has no way to reach
    (`GOV-P-001`: NPM here is GUI-configured only).
    """

    links = load_console_links_yaml(DEFAULT_CONSOLE_LINKS)

    ConsoleHtmlArtifactGenerator().generate(
        links=links,
        output_path=GENERATED_DIR / "console.html",
    )

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    for name in _SERVED_ARTIFACTS:
        _ensure_public_symlink(PUBLIC_DIR / name, Path("..") / name)

    (PUBLIC_DIR / "index.html").write_text(_INDEX_HTML, encoding="utf-8")

    print(
        f"Console written to {GENERATED_DIR / 'console.html'} "
        f"({len(links)} link(s)); served from {PUBLIC_DIR}"
    )


def _ensure_public_symlink(link_path: Path, target: Path) -> None:
    """
    Create, or leave alone, a relative symlink at `link_path` pointing
    at `target` — idempotent, so re-running `console_render` does not
    fail on a symlink it already made.

    **A real file at `link_path` is a defect this command names, not
    silently overwrites** (`FDN-0003` Article 12: an unexpected state
    is stated, never healed past) — nothing else in this codebase
    writes into `PUBLIC_DIR`, so a plain file there means someone put
    it there by hand, and clobbering it would destroy work this
    command has no way to know is disposable.
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
