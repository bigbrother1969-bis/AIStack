from __future__ import annotations

from aistack.config import configured

import json
import socket
import subprocess
from pathlib import Path

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.console.yaml import load_console_links_yaml
from aistack.contracts.health_score import HealthScoreWeights
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.console.identity import load_console_identity
from aistack.generators.console import ConsoleHtmlArtifactGenerator
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.hosts.health import hosts_domain
from aistack.data_budget.health import data_budget_domain
from aistack.health.score import compute_health_score
from aistack.health.score_weights import health_score_weights
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
from aistack.pra.scheduled import with_scheduled
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

DEFAULT_CONSOLE_LINKS = (
    configured(Path(__file__).resolve().parents[1]
    / "console"
    / "definitions"
    / "console_links.yml")
)

# Resolves the `service:` entries of `console_links.yml`.
DEFAULT_INSTANCE_CONFIG = (
    configured(Path(__file__).resolve().parents[1]
    / "instance"
    / "definitions"
    / "instance_config.yml")
)

# The defaults and domain functions below duplicate `aistack.cli.health_render`
# on purpose: no CLI imports another. `test_console_render.py` guards
# against drift between the two.
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

# OPS-0009's declared PRA test records; not scoped by host.
DEFAULT_PRA_TESTS = (
    configured(Path(__file__).resolve().parents[1] / "pra" / "definitions" / "pra_tests.yml")
)

DEFAULT_BACKUP_STRATEGY = (
    configured(Path(__file__).resolve().parents[1]
    / "backup_strategy"
    / "definitions"
    / "backup_strategy.yml")
)

DEFAULT_CATEGORIZATION = (
    configured(Path(__file__).resolve().parents[1]
    / "architecture"
    / "definitions"
    / "service_categorization.yml")
)

# Cwd-relative: an output of `network_docker_discover`, not a shipped definition.
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
        # Instantaneous state plus restart loops from the docker-events
        # history, which catch a container that reads `running` between crashes.
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
        # The scheduled restore tests' outcomes, when more recent.
        readings = with_scheduled(readings)
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
        # A state no engine covers has nothing to restore-test: the
        # uncovered-state finding already names it.
        stateful_services = [d.service for d in declarations if d.has_state and d.covered]
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
        # `backup_strategy.yml` is optional here: without it, only
        # `find_pra_test_gaps` runs.
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
            hosts_domain(),
            data_budget_domain(),
        )
    )


def technical_debt_score(
    cockpit: HealthCockpit,
    weights: HealthScoreWeights | None,
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

    groups = tuple(tuple(domain.findings) for domain in cockpit.domains)

    return compute_technical_debt_score(groups, points), ""


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

    cockpit = build_cockpit(socket.gethostname())
    weights, score_note = health_score_weights(DEFAULT_HEALTH_SCORE_WEIGHTS)
    score = compute_health_score(cockpit, weights) if weights is not None else None
    debt_score, debt_score_note = technical_debt_score(cockpit, weights)

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
