"""
The health cockpit's domains, and the one place that builds it.

`aistack.cli.health_render`, `aistack.cli.console_render` and
`aistack.troubleshooting.findings` each held a copy of these functions
(`GOV-0002/OS-093`); they now call this module. The files a domain reads
are declared once, in `HealthSources`: a caller that needs other ones
replaces `SOURCES` (a test does, a host never needs to).

A domain with nothing to observe on this host (no threshold file, Docker
unreachable, no definition) is `instrumented=False` with a note, never a
false "healthy".
"""

from __future__ import annotations

from aistack.config import configured

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.data_budget.health import data_budget_domain
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.hosts.health import hosts_domain
from aistack.kernel.bootstrap import registered_providers
from aistack.kernel.registries import ProviderRegistry
from aistack.pra.scheduled import with_scheduled
from aistack.pra.yaml import load_pra_tests_yaml
from aistack.providers.docker import DockerProvider
from aistack.providers.filesystem import (
    BackupProvider,
    StorageProvider,
    backup_thresholds_for_host,
    storage_thresholds_for_host,
)
from aistack.providers.gpu import NvidiaGpuProvider, gpu_thresholds_for_host
from aistack.runtime.backup_gap import find_backup_gaps
from aistack.runtime.container_distress import find_container_distress
from aistack.runtime.evaluate_backup import evaluate_backup
from aistack.runtime.evaluate_gpu import evaluate_gpu
from aistack.runtime.evaluate_inventory_gap import evaluate_inventory_gap
from aistack.runtime.evaluate_pra_tests import evaluate_pra_tests
from aistack.runtime.evaluate_services import evaluate_services
from aistack.runtime.evaluate_storage import evaluate_storage
from aistack.runtime.evaluate_uncovered_state import evaluate_uncovered_state
from aistack.runtime.gpu_anomaly import find_gpu_anomalies
from aistack.runtime.inventory_gap import (
    discovered_containers_from_network_observation,
    find_inventory_gaps,
)
from aistack.runtime.pra_test_gap import find_pra_test_gaps, find_undeclared_pra_tests
from aistack.runtime.restart_loop import restart_loop_findings
from aistack.runtime.storage_shortage import find_storage_shortage
from aistack.runtime.uncovered_state_gap import find_uncovered_state

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]

NETWORK_OBSERVATION = Path("reports") / "generated" / "network-docker-observation.json"


def _network_observation() -> Path:
    """
    The last `network_docker_discover` output: the working directory's
    data directory first (the application's, when a service was started
    from elsewhere), else the checkout's. Anchoring on the checkout alone
    points inside site-packages in the Docker image.
    """

    here = Path.cwd() / NETWORK_OBSERVATION

    return here if here.exists() else REPOSITORY_ROOT / NETWORK_OBSERVATION


@dataclass(frozen=True)
class HealthSources:
    """The files the cockpit, its scores and the assistant's CPU check read."""

    # Declared thresholds, scoped by host (OPS-0005, OPS-0006, OPS-0007).
    storage_thresholds: Path = configured(
        PACKAGE_ROOT / "providers" / "filesystem" / "definitions" / "storage_thresholds.yml"
    )
    backup_thresholds: Path = configured(
        PACKAGE_ROOT / "providers" / "filesystem" / "definitions" / "backup_thresholds.yml"
    )
    gpu_thresholds: Path = configured(
        PACKAGE_ROOT / "providers" / "gpu" / "definitions" / "gpu_thresholds.yml"
    )
    # Fleet-wide facts, not scoped by host (OPS-0009, OPS-0010).
    pra_tests: Path = configured(PACKAGE_ROOT / "pra" / "definitions" / "pra_tests.yml")
    backup_strategy: Path = configured(
        PACKAGE_ROOT / "backup_strategy" / "definitions" / "backup_strategy.yml"
    )
    categorization: Path = configured(
        PACKAGE_ROOT / "architecture" / "definitions" / "service_categorization.yml"
    )
    # An output, not a shipped definition; optional data.
    network_docker_observation: Path = field(default_factory=lambda: _network_observation())
    # The health-score weights (OPS-0008), not scoped by host.
    score_weights: Path = configured(
        PACKAGE_ROOT / "health" / "definitions" / "health_score_weights.yml"
    )
    # Resolves the Troubleshooting Assistant's LAN address.
    instance_config: Path = configured(
        PACKAGE_ROOT / "instance" / "definitions" / "instance_config.yml"
    )
    # The assistant's CPU consumption check (`aistack.troubleshooting.findings`).
    resource_priority: Path = configured(
        PACKAGE_ROOT / "priority" / "definitions" / "resource_priority.yml"
    )


SOURCES = HealthSources()


def storage_domain(hostname: str, providers: ProviderRegistry | None = None) -> HealthDomain:
    """
    Storage: mounts of this host that crossed their OPS-0005 thresholds.

    Not instrumented when this host declares nothing or the file is unreadable.
    """

    thresholds, note = storage_thresholds_for_host(
        SOURCES.storage_thresholds, hostname
    )

    if not thresholds:
        return HealthDomain(name="Stockage", instrumented=False, note=note)

    usage = registered_providers(providers).get_as("storage", StorageProvider).collect_usage(
        tuple(threshold.mount for threshold in thresholds)
    )
    shortages = find_storage_shortage(usage, thresholds)

    return HealthDomain(
        name="Stockage", instrumented=True, findings=evaluate_storage(shortages)
    )


def services_domain(providers: ProviderRegistry | None = None) -> HealthDomain:
    """
    Services: restarting, unhealthy or crash-looping containers (OPS-0004).

    Uses the local Docker daemon only; a host without one reads as not instrumented.
    """

    try:
        readings = (
            registered_providers(providers).get_as("docker", DockerProvider).collect_container_states()
        )
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


def backup_domain(hostname: str, providers: ProviderRegistry | None = None) -> HealthDomain:
    """
    Backup: declared backup paths of this host that are missing or stale (OPS-0006).

    Existence and freshness only; restore tests are `pra_tests_domain`.
    """

    thresholds, note = backup_thresholds_for_host(
        SOURCES.backup_thresholds, hostname
    )

    if not thresholds:
        return HealthDomain(name="Sauvegarde / PRA", instrumented=False, note=note)

    freshness = registered_providers(providers).get_as("backup", BackupProvider).collect_freshness(
        tuple(threshold.path for threshold in thresholds)
    )
    gaps = find_backup_gaps(freshness, thresholds)

    return HealthDomain(
        name="Sauvegarde / PRA", instrumented=True, findings=evaluate_backup(gaps)
    )


def gpu_domain(hostname: str, providers: ProviderRegistry | None = None) -> HealthDomain:
    """
    GPU: readings that crossed this host's OPS-0007 thresholds.

    Thresholds declared but no `nvidia-smi` reading reads as instrumented and clean.
    """

    thresholds, note = gpu_thresholds_for_host(SOURCES.gpu_thresholds, hostname)

    if not thresholds:
        return HealthDomain(name="GPU", instrumented=False, note=note)

    readings = registered_providers(providers).get_as("gpu", NvidiaGpuProvider).collect_readings()
    anomalies = find_gpu_anomalies(readings, thresholds)

    return HealthDomain(name="GPU", instrumented=True, findings=evaluate_gpu(anomalies))


def pra_tests_domain() -> HealthDomain:
    """
    Restore tests: services untested, stale or failed against OPS-0009.

    Not host-scoped. Also flags covered stateful services of
    `backup_strategy.yml` (OPS-0010) with no restore test at all; that
    file is optional here.
    """

    if not SOURCES.pra_tests.exists():
        return HealthDomain(
            name="Tests PRA",
            instrumented=False,
            note=(
                f"no PRA test definition at {SOURCES.pra_tests}; restore "
                f"tests are not checked"
            ),
        )

    try:
        readings, thresholds = load_pra_tests_yaml(SOURCES.pra_tests)
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
        declarations = load_backup_strategy_yaml(SOURCES.backup_strategy)
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
    """
    Persistent state: declared stateful services no backup engine covers (OPS-0010).

    Not host-scoped.
    """

    if not SOURCES.backup_strategy.exists():
        return HealthDomain(
            name="État persistant",
            instrumented=False,
            note=(
                f"no backup strategy definition at {SOURCES.backup_strategy}; "
                f"state coverage is not checked"
            ),
        )

    try:
        declarations = load_backup_strategy_yaml(SOURCES.backup_strategy)
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


def inventory_gap_domain(providers: ProviderRegistry | None = None) -> HealthDomain:
    """
    Inventory: containers declared in `service_categorization.yml` but not
    found running, or running but not declared.

    Local containers come from Docker; other LAN hosts from the last
    `network_docker_discover` output, which is optional.
    """

    if not SOURCES.categorization.exists():
        return HealthDomain(
            name="Écarts d'inventaire",
            instrumented=False,
            note=(
                f"no service categorization at {SOURCES.categorization}; "
                f"inventory is not checked"
            ),
        )

    try:
        categorization = load_service_categorization_yaml(SOURCES.categorization)
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
        docker_catalog = DockerRuntimeCatalogBuilder().build(
            registered_providers(providers).collecting("docker").collect()
        )
        discovered: dict[str, str | None] = {
            item.id: None
            for item in docker_catalog.items
            if item.kind == "container"
        }
    except (subprocess.SubprocessError, OSError):
        # Docker unreachable: local containers are not added.
        discovered = {}

    if SOURCES.network_docker_observation.exists():
        try:
            observation = json.loads(
                SOURCES.network_docker_observation.read_text(encoding="utf-8")
            )
            discovered.update(discovered_containers_from_network_observation(observation))
        except (ValueError, OSError):
            # Optional: an unreadable file narrows this to local containers.
            pass

    gaps = find_inventory_gaps(categorization, discovered)

    return HealthDomain(
        name="Écarts d'inventaire",
        instrumented=True,
        findings=evaluate_inventory_gap(gaps),
    )


def build_cockpit(hostname: str, providers: ProviderRegistry | None = None) -> HealthCockpit:
    # One Kernel for the whole cockpit: every domain reads through the
    # same registered providers.
    providers = registered_providers(providers)

    return HealthCockpit(
        domains=(
            storage_domain(hostname, providers),
            services_domain(providers),
            backup_domain(hostname, providers),
            gpu_domain(hostname, providers),
            pra_tests_domain(),
            uncovered_state_domain(),
            inventory_gap_domain(providers),
            hosts_domain(),
            data_budget_domain(),
        )
    )
