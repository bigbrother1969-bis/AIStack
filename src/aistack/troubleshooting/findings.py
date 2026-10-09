"""
The findings the Troubleshooting Assistant can guide someone through
(`ADR-0012` § 4), collected fresh from the host on each request.

Moved from `troubleshooting_assistant_ui/app.py` on 2026-10-03, where
it sat outside the governed suite; the route in
`aistack.web.troubleshooting` now receives `collect_findings` as a
collaborator, and `qualify` — the collision-safe routing key — is a
pure function the suite tests on its own.

**The cockpit's seven domain builders are still duplicated from
`aistack.cli.health_render`, not imported** — the "no UI imports a CLI
module" choice the screen made on 2026-09-18 and kept on 2026-09-30
(`aistack.cli.console_render` holds a third copy). Moving them is not
what this change is for; folding the three copies into one is a
separate piece of work.

**`/finding/{key}/apply` (2026-09-18).** One fixed, code-known action —
declaring a subject a `background` container in the governed
resource-priority definition, `aistack.troubleshooting.apply` — never
anything derived from the AI's own `recommend` text, and only for a
`CONSUMPTION_DOMAIN` finding (`APPLYABLE_DOMAINS`).

**Widened to the full Cockpit Santé, 2026-09-30** (the owner: "les
findings en rouge doivent être cliquables et doivent diriger vers une
explication en français... avec la possibilité de résoudre le problème
de façon accompagnée par les modules d'IA"): every domain
`build_cockpit` assembles reaches the assistant's `reason` / `explain`
/ `recommend` chain, not only the original CPU/consumption check.
"""

from __future__ import annotations

from aistack.config import configured

import json
import socket
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.hosts.health import hosts_domain
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
    # Anchored on the checkout, not the working directory: a systemd
    # service's working directory is not guaranteed to be the
    # repository root. Optional, best-effort data either way.
    network_docker_observation: Path = (
        REPOSITORY_ROOT / "reports" / "generated" / "network-docker-observation.json"
    )


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
    Every `RuntimeFinding` `aistack.runtime.evaluate.evaluate` can
    produce right now, freshly collected — same real subject as
    `aistack.cli.ai_reason.qualified_findings`, duplicated rather than
    imported (see module docstring above). Formerly this module's own
    `qualified_findings()`, renamed 2026-09-30 when that name became
    the widened union below: this is now only the CPU/temperature
    half of it, tagged `CONSUMPTION_DOMAIN`.
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


# The seven domain-builder functions and `build_cockpit` below mirror
# `aistack.cli.health_render`'s own exactly (same primitives, same
# findings) — duplicated, not imported, per this module's own docstring
# above. Trimmed to a one-line "mirrors" docstring each, the same
# convention `aistack.cli.console_render`'s own duplicate copies
# already use — the full rationale for each domain lives once, in
# `health_render.py`.


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
        # Instantaneous state (restarting/unhealthy), plus restart loops
        # counted from the docker-events history — the second catches a
        # container that reads `running` between two crashes (mularr,
        # 2026-10-02, `aistack.runtime.restart_loop`).
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
        # The scheduled restore tests' outcomes, when more recent (2.0).
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
        # uncovered-state finding already names it (2026-10-08).
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
        # The same tolerant absence `services_domain` already holds for
        # an unreachable local Docker daemon — local containers are
        # simply not added, never treated as "none exist".
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
            # The last network discovery is optional, best-effort data
            # — a corrupt or unreadable file narrows this render to a
            # local-only reconciliation rather than failing the domain.
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
        )
    )


# The pseudo-domain name for `_consumption_findings()`'s own output —
# `find_unexplained_consumption`/`evaluate` predate `PLAN-J7`'s cockpit
# and are never one of `build_cockpit`'s seven `HealthDomain`s, so this
# assistant gives their findings the same French, human-facing label
# the cockpit's own seven domains already carry, rather than leaving
# them domain-less. Never written to any `HealthDomain.name` anywhere
# else — this assistant's own vocabulary, not the cockpit's.
CONSUMPTION_DOMAIN = "Consommation CPU"

# Only a `CONSUMPTION_DOMAIN` finding may reach `/finding/{key}/apply`
# — the owner's explicit confirmation, unchanged by this widening, that
# the apply button "reste réservé à son action fixe déjà cadrée" (see
# `apply()`'s own docstring below). A `frozenset`: membership only.
APPLYABLE_DOMAINS = frozenset({CONSUMPTION_DOMAIN})


class QualifiedFinding(NamedTuple):
    """
    One finding `qualified_findings()` assembled, tagged with its
    domain of origin and a routing key that is *not* always
    `finding.subject`.

    **Why a separate `key`.** `RuntimeFinding.subject` is drawn from
    each domain's own identifier space — a service name, a container
    name, a mount path, a GPU name — and nothing stops two different
    domains from naming the same subject: confirmed 2026-09-30,
    "gigabyte", "nextcloud" and "immich" are each flagged *today* by
    both Tests PRA (`evaluate_pra_tests`) and État persistant
    (`evaluate_uncovered_state`). Routing on the bare subject alone
    (`next(f for f in findings if f.subject == subject)`, this
    module's own pattern before this widening) would silently pick
    only the first match, hiding the second real, distinct anomaly —
    exactly the "jamais un faux sain" `FDN-0003` Article 12 already
    forbids elsewhere in this codebase. `key` is `finding.subject`
    unchanged when it is unique across this call's own assembled set
    (the ordinary case, and the whole set before this widening), and
    `f"{domain}::{finding.subject}"` only when it collides — paid only
    where it is actually needed, every existing URL for an
    already-unique subject stays exactly as it was.

    `finding.subject` itself is never mutated — `reason`/`explain`/
    `recommend`'s own prompts and `apply()`'s own
    `ContainerPriorityDefinition(name=...)` write both still need the
    real subject, not this routing key.
    """

    key: str
    domain: str
    finding: RuntimeFinding

    @property
    def applyable(self) -> bool:
        return self.domain in APPLYABLE_DOMAINS


def qualified_findings() -> tuple[tuple[QualifiedFinding, ...], str]:
    """
    Every `RuntimeFinding` this assistant can currently guide someone
    through, freshly collected — `_consumption_findings()`'s own CPU/
    temperature check (tagged `CONSUMPTION_DOMAIN`), unioned with
    every domain `build_cockpit(socket.gethostname())` assembles
    (tagged with that domain's own real `HealthDomain.name`), the
    2026-09-30 widening the owner cadred as "Élargir + relier" (see
    module docstring above). An uninstrumented cockpit domain (no
    threshold file, `nvidia-smi` unreachable, and so on) simply
    contributes no findings here, the same honest absence
    `health.html`/`console.html` already state for it in their own,
    separate domain-status rendering — this page's own job is only to
    list findings ready to be guided, not to restate instrumentation
    status a second time.

    `note` keeps its pre-widening meaning: a hard stop before any
    finding could be computed at all (no resource-priority definition,
    Docker unreachable for the CPU check) — never a per-domain
    absence note, which stays `health.html`'s own to state.
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
