from __future__ import annotations

from aistack.config import configured

import json
from datetime import date
import socket
import subprocess
from pathlib import Path

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.console.yaml import load_console_links_yaml
from aistack.contracts.health_score import HealthScoreWeights
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.console.identity import load_console_identity
from aistack.generators.console import ConsoleHtmlArtifactGenerator
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.score import compute_health_score
from aistack.health.score_weights import health_score_weights
from aistack.health.quarantine import quarantine_findings
from aistack.health.technical_debt import compute_technical_debt_score
from aistack.i18n import default_languages
from aistack.i18n.pages import page_file
from aistack.instance.yaml import load_instance_config_yaml
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
from aistack.runtime.evaluate_inventory_gap import evaluate_inventory_gap
from aistack.runtime.evaluate_pra_tests import evaluate_pra_tests
from aistack.runtime.evaluate_services import evaluate_services
from aistack.runtime.restart_loop import restart_loop_findings
from aistack.runtime.evaluate_storage import evaluate_storage
from aistack.runtime.evaluate_uncovered_state import evaluate_uncovered_state
from aistack.runtime.gpu_anomaly import find_gpu_anomalies
from aistack.runtime.inventory_gap import (
    discovered_containers_from_network_observation,
    find_inventory_gaps,
)
from aistack.runtime.pra_test_gap import find_pra_test_gaps, find_undeclared_pra_tests
from aistack.runtime.storage_shortage import find_storage_shortage
from aistack.runtime.uncovered_state_gap import find_uncovered_state

# Same convention as `architecture_render.py`'s own
# `DEFAULT_CATEGORIZATION` — a `Path(__file__).resolve()`-relative
# default, not `importlib.resources`.
DEFAULT_CONSOLE_LINKS = (
    configured(Path(__file__).resolve().parents[1]
    / "console"
    / "definitions"
    / "console_links.yml")
)

# R10, 2026-09-30 — resolves `DEFAULT_CONSOLE_LINKS`'s own `service:`
# entries. Declared explicitly here, the same as every other default
# above and below, rather than left to `load_console_links_yaml`'s own
# internal fallback (which exists for a convenience caller — a
# mini-app's `app.py`, a test — not for this CLI, which already names
# every one of its other inputs by its own path).
DEFAULT_INSTANCE_CONFIG = (
    configured(Path(__file__).resolve().parents[1]
    / "instance"
    / "definitions"
    / "instance_config.yml")
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
    configured(Path(__file__).resolve().parents[1]
    / "providers"
    / "filesystem"
    / "definitions"
    / "storage_thresholds.yml")
)

DEFAULT_BACKUP_THRESHOLDS = (
    configured(Path(__file__).resolve().parents[1]
    / "providers"
    / "filesystem"
    / "definitions"
    / "backup_thresholds.yml")
)

DEFAULT_GPU_THRESHOLDS = (
    configured(Path(__file__).resolve().parents[1]
    / "providers"
    / "gpu"
    / "definitions"
    / "gpu_thresholds.yml")
)

DEFAULT_HEALTH_SCORE_WEIGHTS = (
    configured(Path(__file__).resolve().parents[1]
    / "health"
    / "definitions"
    / "health_score_weights.yml")
)

# `OPS-0009`'s own declared PRA test records — not scoped by host, the
# same reason `DEFAULT_HEALTH_SCORE_WEIGHTS` is not. Mirrors
# `aistack.cli.health_render.DEFAULT_PRA_TESTS` exactly — this module
# never imports the other, per this file's own "no CLI in this
# package imports another" convention (see the comment above).
DEFAULT_PRA_TESTS = (
    configured(Path(__file__).resolve().parents[1] / "pra" / "definitions" / "pra_tests.yml")
)

DEFAULT_BACKUP_STRATEGY = (
    configured(Path(__file__).resolve().parents[1]
    / "backup_strategy"
    / "definitions"
    / "backup_strategy.yml")
)

# Mirrors `aistack.cli.health_render.DEFAULT_CATEGORIZATION` exactly —
# this module never imports the other, per this file's own "no CLI in
# this package imports another" convention (see the comment above).
DEFAULT_CATEGORIZATION = (
    configured(Path(__file__).resolve().parents[1]
    / "architecture"
    / "definitions"
    / "service_categorization.yml")
)

# Mirrors `aistack.cli.health_render.DEFAULT_NETWORK_DOCKER_OBSERVATION`
# exactly — the cwd-relative convention `network_docker_discover.main`
# itself uses for this same output path, not the
# `Path(__file__).resolve()`-relative convention the constants above
# hold, since this names an output, not a shipped definition. A plain
# literal, not `GENERATED_DIR / ...`: that constant is declared much
# further down this module, next to `main()`, and every domain
# function above it already runs before `main` does.
DEFAULT_NETWORK_DOCKER_OBSERVATION = Path(
    "reports/generated/network-docker-observation.json"
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
        name="Services",
        instrumented=True,
        # Instantaneous state (restarting/unhealthy), plus restart loops
        # counted from the docker-events history — the second catches a
        # container that reads `running` between two crashes (mularr,
        # 2026-10-02, `aistack.runtime.restart_loop`).
        findings=evaluate_services(distress) + restart_loop_findings(),
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

    try:
        declarations = load_backup_strategy_yaml(DEFAULT_BACKUP_STRATEGY)
        stateful_services = [d.service for d in declarations if d.has_state]
        declared_services = [reading.service for reading in readings]
        observed_at = readings[0].observed_at if readings else None

        if observed_at is not None:
            gaps = gaps + find_undeclared_pra_tests(
                stateful_services,
                declared_services,
                thresholds.thresholds,
                observed_at,
            )
    except (ValueError, OSError):
        # `backup_strategy.yml` is optional, best-effort data for this
        # one check — its absence or corruption narrows this render to
        # the three reasons `find_pra_test_gaps` alone already
        # detects, never failing the whole domain.
        pass

    return HealthDomain(
        name="Tests PRA", instrumented=True, findings=evaluate_pra_tests(gaps)
    )


def uncovered_state_domain() -> HealthDomain:
    """Mirrors `aistack.cli.health_render.uncovered_state_domain` exactly."""

    if not DEFAULT_BACKUP_STRATEGY.exists():
        return HealthDomain(
            name="État persistant",
            instrumented=False,
            note=(
                f"no backup strategy definition at {DEFAULT_BACKUP_STRATEGY}; "
                f"state coverage is not checked"
            ),
        )

    try:
        declarations = load_backup_strategy_yaml(DEFAULT_BACKUP_STRATEGY)
    except (ValueError, OSError) as error:
        return HealthDomain(
            name="État persistant",
            instrumented=False,
            note=(
                f"backup strategy definition not readable ({error}); state "
                f"coverage is not checked"
            ),
        )

    gaps = find_uncovered_state(declarations)

    return HealthDomain(
        name="État persistant",
        instrumented=True,
        findings=evaluate_uncovered_state(gaps),
    )


def inventory_gap_domain() -> HealthDomain:
    """Mirrors `aistack.cli.health_render.inventory_gap_domain` exactly."""

    if not DEFAULT_CATEGORIZATION.exists():
        return HealthDomain(
            name="Écarts d'inventaire",
            instrumented=False,
            note=(
                f"no service categorization at {DEFAULT_CATEGORIZATION}; "
                f"inventory is not checked"
            ),
        )

    try:
        categorization = load_service_categorization_yaml(DEFAULT_CATEGORIZATION)
    except (ValueError, OSError) as error:
        return HealthDomain(
            name="Écarts d'inventaire",
            instrumented=False,
            note=(
                f"service categorization not readable ({error}); "
                f"inventory is not checked"
            ),
        )

    try:
        docker_catalog = DockerRuntimeCatalogBuilder().build(DockerProvider().collect())
        discovered: dict[str, str | None] = {
            item.id: None
            for item in docker_catalog.items
            if item.kind == "container"
        }
    except (subprocess.SubprocessError, OSError):
        discovered = {}

    if DEFAULT_NETWORK_DOCKER_OBSERVATION.exists():
        try:
            observation = json.loads(
                DEFAULT_NETWORK_DOCKER_OBSERVATION.read_text(encoding="utf-8")
            )
            discovered.update(discovered_containers_from_network_observation(observation))
        except (ValueError, OSError):
            pass

    gaps = find_inventory_gaps(categorization, discovered)

    return HealthDomain(
        name="Écarts d'inventaire",
        instrumented=True,
        findings=evaluate_inventory_gap(gaps),
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
            uncovered_state_domain(),
            inventory_gap_domain(),
        )
    )


def technical_debt_score(
    cockpit: HealthCockpit,
    weights: HealthScoreWeights | None,
    quarantine: tuple[RuntimeFinding, ...] = (),
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

    # The quarantined code (`OPS-0012`, 2026-10-05) counts as one more
    # group beside the domains: debt, but not a domain of the host.
    groups = tuple(tuple(domain.findings) for domain in cockpit.domains)
    if quarantine:
        groups += (quarantine,)

    return compute_technical_debt_score(groups, points), ""


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

    **Serving the pages is not this command's job** —
    `deploy/systemd/aistack-web.service` runs AIStack's single web
    application (`ADR-0012`; `aistack-console.service` and its static
    file server before 2026-10-03, `PLAN-J11` § 4), and pointing a reverse-proxy Host at that server is a manual Nginx
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

    **One console per declared language, since 2026-09-27** (ADR-0010
    § 5). The cockpit and its scores are computed once — the host is
    the same whatever language the page is read in — and the page is
    written once per language: the reference keeps `console.html` and
    its history stream, every other language adds
    `console.<code>.html` beside it. `aistack.web.console` picks one
    per request. `PUBLIC_DIR` keeps its reference-language symlinks: the
    new server does not read it, but a host that has to fall back to the
    old `http.server` launcher still finds the three pages there.
    """

    languages = default_languages()

    cockpit = build_cockpit(socket.gethostname())
    weights, score_note = health_score_weights(DEFAULT_HEALTH_SCORE_WEIGHTS)
    score = compute_health_score(cockpit, weights) if weights is not None else None
    quarantine, _readings, _note = quarantine_findings(date.today())
    debt_score, debt_score_note = technical_debt_score(cockpit, weights, quarantine)

    written: list[str] = []
    links_count = 0
    instance = load_instance_config_yaml(DEFAULT_INSTANCE_CONFIG)

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
