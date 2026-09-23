from __future__ import annotations

import socket
import subprocess
from pathlib import Path

from aistack.console.yaml import load_console_links_yaml
from aistack.contracts.health_score import HealthScoreWeights
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.generators.console import ConsoleHtmlArtifactGenerator
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.score import compute_health_score
from aistack.health.score_weights import health_score_weights
from aistack.health.technical_debt import compute_technical_debt_score
from aistack.providers.docker import DockerProvider
from aistack.providers.filesystem import (
    BackupProvider,
    StorageProvider,
    backup_thresholds_for_host,
    storage_thresholds_for_host,
)
from aistack.pra.yaml import load_pra_tests_yaml
from aistack.providers.gpu import NvidiaGpuProvider, gpu_thresholds_for_host
from aistack.runtime.backup_gap import find_backup_gaps
from aistack.runtime.container_distress import find_container_distress
from aistack.runtime.evaluate_backup import evaluate_backup
from aistack.runtime.evaluate_gpu import evaluate_gpu
from aistack.runtime.evaluate_pra_tests import evaluate_pra_tests
from aistack.runtime.evaluate_services import evaluate_services
from aistack.runtime.evaluate_storage import evaluate_storage
from aistack.runtime.gpu_anomaly import find_gpu_anomalies
from aistack.runtime.pra_test_gap import find_pra_test_gaps
from aistack.runtime.storage_shortage import find_storage_shortage

# Same convention as `architecture_render.py`'s own
# `DEFAULT_CATEGORIZATION` — a `Path(__file__).resolve()`-relative
# default, not `importlib.resources`.
DEFAULT_CONSOLE_LINKS = (
    Path(__file__).resolve().parents[1]
    / "console"
    / "definitions"
    / "console_links.yml"
)

# **Duplicated from `aistack.cli.health_render`, not imported —
# deliberately, added 2026-09-13** (`claude/PLAN-J11-CONSOLE
# -2026-09-11.md` § 11.9, the health cartouche closing the owner's own
# gap analysis against the historical `architecture.html` reference
# page). This is the exact same choice `health_render.py` itself
# already made and documents for `DEFAULT_STORAGE_THRESHOLDS`/
# `DEFAULT_BACKUP_THRESHOLDS`/`DEFAULT_GPU_THRESHOLDS` against
# `runtime_diagnose.py`: "no CLI in this package imports another" — a
# `HealthCockpit` snapshot is cheap enough to build twice (this
# console generates once, on demand, not on a hot path) and the
# alternative is a third CLI importing a second CLI's `main()`-adjacent
# helpers, which this heritage has never done. `test_console_render.py`
# carries the same drift-guard tests `test_health_render.py` already
# has against `runtime_diagnose.py`, extended to check this module's
# four threshold paths and its weights path against
# `aistack.cli.health_render`'s own.
DEFAULT_STORAGE_THRESHOLDS = (
    Path(__file__).resolve().parents[1]
    / "providers"
    / "filesystem"
    / "definitions"
    / "storage_thresholds.yml"
)

DEFAULT_BACKUP_THRESHOLDS = (
    Path(__file__).resolve().parents[1]
    / "providers"
    / "filesystem"
    / "definitions"
    / "backup_thresholds.yml"
)

DEFAULT_GPU_THRESHOLDS = (
    Path(__file__).resolve().parents[1]
    / "providers"
    / "gpu"
    / "definitions"
    / "gpu_thresholds.yml"
)

DEFAULT_HEALTH_SCORE_WEIGHTS = (
    Path(__file__).resolve().parents[1]
    / "health"
    / "definitions"
    / "health_score_weights.yml"
)

# `OPS-0009`'s own declared PRA test records — not scoped by host, the
# same reason `DEFAULT_HEALTH_SCORE_WEIGHTS` is not. Mirrors
# `aistack.cli.health_render.DEFAULT_PRA_TESTS` exactly — this module
# never imports the other, per this file's own "no CLI in this
# package imports another" convention (see the comment above).
DEFAULT_PRA_TESTS = (
    Path(__file__).resolve().parents[1] / "pra" / "definitions" / "pra_tests.yml"
)


def storage_domain(hostname: str) -> HealthDomain:
    """Mirrors `aistack.cli.health_render.storage_domain` exactly."""

    thresholds, note = storage_thresholds_for_host(
        DEFAULT_STORAGE_THRESHOLDS, hostname
    )

    if not thresholds:
        return HealthDomain(name="Stockage", instrumented=False, note=note)

    usage = StorageProvider().collect_usage(
        tuple(threshold.mount for threshold in thresholds)
    )
    shortages = find_storage_shortage(usage, thresholds)

    return HealthDomain(
        name="Stockage", instrumented=True, findings=evaluate_storage(shortages)
    )


def services_domain() -> HealthDomain:
    """Mirrors `aistack.cli.health_render.services_domain` exactly."""

    try:
        readings = DockerProvider().collect_container_states()
    except (subprocess.SubprocessError, OSError) as error:
        return HealthDomain(
            name="Services",
            instrumented=False,
            note=(
                f"container states could not be collected ({error}); "
                f"service health is not checked"
            ),
        )

    distress = find_container_distress(readings)

    return HealthDomain(
        name="Services", instrumented=True, findings=evaluate_services(distress)
    )


def backup_domain(hostname: str) -> HealthDomain:
    """Mirrors `aistack.cli.health_render.backup_domain` exactly."""

    thresholds, note = backup_thresholds_for_host(
        DEFAULT_BACKUP_THRESHOLDS, hostname
    )

    if not thresholds:
        return HealthDomain(name="Sauvegarde / PRA", instrumented=False, note=note)

    freshness = BackupProvider().collect_freshness(
        tuple(threshold.path for threshold in thresholds)
    )
    gaps = find_backup_gaps(freshness, thresholds)

    return HealthDomain(
        name="Sauvegarde / PRA", instrumented=True, findings=evaluate_backup(gaps)
    )


def gpu_domain(hostname: str) -> HealthDomain:
    """Mirrors `aistack.cli.health_render.gpu_domain` exactly."""

    thresholds, note = gpu_thresholds_for_host(DEFAULT_GPU_THRESHOLDS, hostname)

    if not thresholds:
        return HealthDomain(name="GPU", instrumented=False, note=note)

    readings = NvidiaGpuProvider().collect_readings()
    anomalies = find_gpu_anomalies(readings, thresholds)

    return HealthDomain(name="GPU", instrumented=True, findings=evaluate_gpu(anomalies))


def pra_tests_domain() -> HealthDomain:
    """Mirrors `aistack.cli.health_render.pra_tests_domain` exactly."""

    if not DEFAULT_PRA_TESTS.exists():
        return HealthDomain(
            name="Tests PRA",
            instrumented=False,
            note=(
                f"no PRA test definition at {DEFAULT_PRA_TESTS}; restore "
                f"tests are not checked"
            ),
        )

    try:
        readings, thresholds = load_pra_tests_yaml(DEFAULT_PRA_TESTS)
    except (ValueError, OSError) as error:
        return HealthDomain(
            name="Tests PRA",
            instrumented=False,
            note=(
                f"PRA test definition not readable ({error}); restore "
                f"tests are not checked"
            ),
        )

    gaps = find_pra_test_gaps(readings, thresholds.thresholds)

    return HealthDomain(
        name="Tests PRA", instrumented=True, findings=evaluate_pra_tests(gaps)
    )


def build_cockpit(hostname: str) -> HealthCockpit:
    """Mirrors `aistack.cli.health_render.build_cockpit` exactly."""

    return HealthCockpit(
        domains=(
            storage_domain(hostname),
            services_domain(),
            backup_domain(hostname),
            gpu_domain(hostname),
            pra_tests_domain(),
        )
    )


def technical_debt_score(
    cockpit: HealthCockpit, weights: HealthScoreWeights | None
) -> tuple[TechnicalDebtScore | None, str]:
    """Mirrors `aistack.cli.health_render.technical_debt_score` exactly."""

    if weights is None:
        return None, (
            "no health-score weight definition available; technical-debt "
            "score is not computed"
        )

    points = weights.for_domain("Services")

    if points is None:
        raise ValueError(
            "OPS-0008 declares no weight for domain 'Services'; the "
            "technical-debt score reuses it and cannot be computed "
            "without it"
        )

    findings = tuple(
        finding for domain in cockpit.domains for finding in domain.findings
    )

    return compute_technical_debt_score(findings, points), ""


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

    **Builds and passes a `HealthCockpit`/`HealthScore`, added
    2026-09-13** (`PLAN-J11` § 11.9) — the same score `health_render
    .main()` computes, from the same declared `OPS-0008` weights,
    handed to `ConsoleHtmlArtifactGenerator.generate` so the console
    shows a summary cartouche above its link grid instead of naming
    the score model twice. `weights is None` (no declared weights
    file) renders the score as an honest note, not a silent omission —
    the same branch `health_render.main` already takes.

    **Also builds and passes a `TechnicalDebtScore`, added 2026-09-23**
    (`PLAN-J11` § 11.9.1) — the same "Dette technique" card
    `health_render.main()` writes, from the same cockpit and weights,
    never a second load of either.
    """

    links = load_console_links_yaml(DEFAULT_CONSOLE_LINKS)

    cockpit = build_cockpit(socket.gethostname())
    weights, score_note = health_score_weights(DEFAULT_HEALTH_SCORE_WEIGHTS)
    score = compute_health_score(cockpit, weights) if weights is not None else None
    debt_score, debt_score_note = technical_debt_score(cockpit, weights)

    ConsoleHtmlArtifactGenerator().generate(
        links=links,
        output_path=GENERATED_DIR / "console.html",
        cockpit=cockpit,
        score=score,
        score_note=score_note,
        technical_debt_score=debt_score,
        technical_debt_note=debt_score_note,
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
