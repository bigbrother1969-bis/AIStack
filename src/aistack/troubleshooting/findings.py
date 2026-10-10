"""
The findings the Troubleshooting Assistant can guide someone through
(`ADR-0012` § 4), collected fresh from the host on each request.

Covers the CPU consumption check plus every Cockpit Santé domain. The
domain builders duplicate those of `aistack.cli.health_render` (and
`aistack.cli.console_render`) because no UI imports a CLI module. Only a
consumption finding can be applied (`aistack.troubleshooting.apply`).
"""

from __future__ import annotations

from aistack.config import configured

import json
import socket
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.hosts.health import hosts_domain
from aistack.data_budget.health import data_budget_domain
from aistack.pra.scheduled import with_scheduled
from aistack.pra.yaml import load_pra_tests_yaml
from aistack.priority.definition import ResourcePriorityDefinition
from aistack.priority.yaml import load_resource_priority_yaml
from aistack.providers.docker import DockerProvider
from aistack.providers.filesystem import (
    BackupProvider,
    StorageProvider,
    backup_thresholds_for_host,
    storage_thresholds_for_host,
)
from aistack.providers.gpu import NvidiaGpuProvider, gpu_thresholds_for_host
from aistack.providers.host.provider import HostProvider
from aistack.runtime.backup_gap import find_backup_gaps
from aistack.runtime.container_distress import find_container_distress
from aistack.runtime.evaluate import evaluate
from aistack.runtime.evaluate_backup import evaluate_backup
from aistack.runtime.evaluate_gpu import evaluate_gpu
from aistack.runtime.evaluate_inventory_gap import evaluate_inventory_gap
from aistack.runtime.evaluate_pra_tests import evaluate_pra_tests
from aistack.runtime.evaluate_services import evaluate_services
from aistack.runtime.evaluate_storage import evaluate_storage
from aistack.runtime.evaluate_uncovered_state import evaluate_uncovered_state
from aistack.runtime.gpu_anomaly import find_gpu_anomalies
from aistack.runtime.idle_consumption import find_unexplained_consumption
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
    """The working directory's data first (the container's `/app`, a
    service started from the checkout), else the checkout's."""

    here = Path.cwd() / NETWORK_OBSERVATION
    return here if here.exists() else REPOSITORY_ROOT / NETWORK_OBSERVATION


@dataclass(frozen=True)
class FindingSources:
    """Every declaration file the collection reads, one field each."""

    resource_priority: Path = configured(PACKAGE_ROOT / "priority" / "definitions" / "resource_priority.yml")
    storage_thresholds: Path = (
        configured(PACKAGE_ROOT / "providers" / "filesystem" / "definitions" / "storage_thresholds.yml")
    )
    backup_thresholds: Path = (
        configured(PACKAGE_ROOT / "providers" / "filesystem" / "definitions" / "backup_thresholds.yml")
    )
    gpu_thresholds: Path = configured(PACKAGE_ROOT / "providers" / "gpu" / "definitions" / "gpu_thresholds.yml")
    pra_tests: Path = configured(PACKAGE_ROOT / "pra" / "definitions" / "pra_tests.yml")
    backup_strategy: Path = (
        configured(PACKAGE_ROOT / "backup_strategy" / "definitions" / "backup_strategy.yml")
    )
    categorization: Path = (
        configured(PACKAGE_ROOT / "architecture" / "definitions" / "service_categorization.yml")
    )
    # The data directory the application serves, else the checkout's;
    # anchoring on the checkout alone points inside site-packages in the
    # Docker image. Optional data.
    network_docker_observation: Path = field(default_factory=lambda: _network_observation())


SOURCES = FindingSources()

def resource_priority_definition(
    path: Path,
) -> tuple[ResourcePriorityDefinition | None, str]:
    """Mirrors `aistack.cli.ai_reason.resource_priority_definition` exactly."""

    if not path.exists():
        return None, (
            f"no resource-priority definition at {path}; consumption "
            f"is not checked"
        )

    try:
        return load_resource_priority_yaml(path), ""
    except (ValueError, OSError) as error:
        return None, (
            f"resource-priority definition not readable ({error}); "
            f"consumption is not checked"
        )


def _consumption_findings() -> tuple[tuple[RuntimeFinding, ...], str]:
    """
    The CPU/temperature findings of `aistack.runtime.evaluate`, freshly
    collected, as in `aistack.cli.ai_reason.qualified_findings`.
    """

    definition, note = resource_priority_definition(SOURCES.resource_priority)

    if definition is None:
        return (), note

    try:
        readings = DockerProvider().collect_cpu_readings()
    except (subprocess.SubprocessError, OSError) as error:
        return (), (
            f"CPU readings could not be collected ({error}); "
            f"nothing to reason about"
        )

    consumption = find_unexplained_consumption(readings, definition)
    temperatures = HostProvider().collect_temperatures()

    return evaluate(consumption, temperatures), ""


# The domain builders below mirror `aistack.cli.health_render`, where each
# domain is documented.


def storage_domain(hostname: str) -> HealthDomain:
    """Mirrors `aistack.cli.health_render.storage_domain` exactly."""

    thresholds, note = storage_thresholds_for_host(
        SOURCES.storage_thresholds, hostname
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
        # Instantaneous state plus restart loops counted from the
        # docker-events history, which catch a container that reads
        # `running` between two crashes.
        findings=evaluate_services(distress) + restart_loop_findings(),
    )


def backup_domain(hostname: str) -> HealthDomain:
    """Mirrors `aistack.cli.health_render.backup_domain` exactly."""

    thresholds, note = backup_thresholds_for_host(SOURCES.backup_thresholds, hostname)

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

    thresholds, note = gpu_thresholds_for_host(SOURCES.gpu_thresholds, hostname)

    if not thresholds:
        return HealthDomain(name="GPU", instrumented=False, note=note)

    readings = NvidiaGpuProvider().collect_readings()
    anomalies = find_gpu_anomalies(readings, thresholds)

    return HealthDomain(name="GPU", instrumented=True, findings=evaluate_gpu(anomalies))


def pra_tests_domain() -> HealthDomain:
    """Mirrors `aistack.cli.health_render.pra_tests_domain` exactly."""

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
        # A state no engine covers has nothing to restore-test; the
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
        # `backup_strategy.yml` is optional here: without it, only the
        # undeclared-service check is skipped.
        pass

    return HealthDomain(
        name="Tests PRA", instrumented=True, findings=evaluate_pra_tests(gaps)
    )


def uncovered_state_domain() -> HealthDomain:
    """Mirrors `aistack.cli.health_render.uncovered_state_domain` exactly."""

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


def inventory_gap_domain() -> HealthDomain:
    """Mirrors `aistack.cli.health_render.inventory_gap_domain` exactly."""

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
        docker_catalog = DockerRuntimeCatalogBuilder().build(DockerProvider().collect())
        discovered: dict[str, str | None] = {
            item.id: None for item in docker_catalog.items if item.kind == "container"
        }
    except (subprocess.SubprocessError, OSError):
        # Docker unreachable: local containers are not added, never read
        # as "none exist".
        discovered = {}

    if SOURCES.network_docker_observation.exists():
        try:
            observation = json.loads(
                SOURCES.network_docker_observation.read_text(encoding="utf-8")
            )
            discovered.update(
                discovered_containers_from_network_observation(observation)
            )
        except (ValueError, OSError):
            # Optional data: an unreadable file limits the check to
            # local containers.
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


# Label for the CPU consumption findings, which come from no cockpit domain.
CONSUMPTION_DOMAIN = "Consommation CPU"

# Only consumption findings may be applied (`/finding/{key}/apply`).
APPLYABLE_DOMAINS = frozenset({CONSUMPTION_DOMAIN})


class QualifiedFinding(NamedTuple):
    """
    One finding with its domain and routing key.

    Two domains can flag the same subject (e.g. a service in both Tests PRA
    and État persistant), so routing on the subject alone would hide one of
    them. `key` is the subject when unique in the set, else
    `"<domain>::<subject>"`. `finding.subject` itself is never changed.
    """

    key: str
    domain: str
    finding: RuntimeFinding

    @property
    def applyable(self) -> bool:
        return self.domain in APPLYABLE_DOMAINS


def qualified_findings() -> tuple[tuple[QualifiedFinding, ...], str]:
    """
    Every finding the assistant can guide someone through: the CPU
    consumption check plus every domain of `build_cockpit`, each tagged
    with its domain. Uninstrumented domains contribute nothing.

    `note` is set only when the consumption check could not run at all.
    """

    consumption_findings, note = _consumption_findings()
    cockpit = build_cockpit(socket.gethostname())

    tagged: list[tuple[str, RuntimeFinding]] = [
        (CONSUMPTION_DOMAIN, finding) for finding in consumption_findings
    ]
    for domain in cockpit.domains:
        tagged.extend((domain.name, finding) for finding in domain.findings)

    return qualify(tagged), note


def qualify(tagged: Iterable[tuple[str, RuntimeFinding]]) -> tuple[QualifiedFinding, ...]:
    """
    Give each (domain, finding) its routing key: the bare subject when
    no other finding in the set shares it, `"<domain>::<subject>"` when
    one does (`QualifiedFinding` says why).
    """

    pairs = list(tagged)
    subject_counts: dict[str, int] = {}

    for _, finding in pairs:
        subject_counts[finding.subject] = subject_counts.get(finding.subject, 0) + 1

    return tuple(
        QualifiedFinding(
            key=(
                finding.subject
                if subject_counts[finding.subject] == 1
                else f"{domain_name}::{finding.subject}"
            ),
            domain=domain_name,
            finding=finding,
        )
        for domain_name, finding in pairs
    )


CollectFindings = Callable[[], "tuple[tuple[QualifiedFinding, ...], str]"]
