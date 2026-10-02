from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.contracts.health_score import HealthScoreWeights
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.generators.health import HealthHtmlArtifactGenerator
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.score import compute_health_score
from aistack.health.score_weights import health_score_weights
from aistack.health.technical_debt import compute_technical_debt_score
from aistack.i18n import default_languages
from aistack.i18n.pages import page_file
from aistack.instance.yaml import load_instance_config_yaml
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

# `OPS-0005`'s own declared thresholds — the same file
# `aistack.cli.runtime_diagnose.DEFAULT_STORAGE_THRESHOLDS` reads.
# Declared again here rather than imported from that module: no CLI
# in this package imports another (`architecture_render.py` composes
# `DockerRuntimeCatalogBuilder`/`ComposeRuntimeCatalogBuilder` itself
# rather than importing `docker_catalog.main`), so each command keeps
# its own copy of the one path both happen to need, the same
# `Path(__file__).resolve()`-relative convention every other
# `DEFAULT_*` constant in this package already uses.
DEFAULT_STORAGE_THRESHOLDS = (
    Path(__file__).resolve().parents[1]
    / "providers"
    / "filesystem"
    / "definitions"
    / "storage_thresholds.yml"
)

# `OPS-0006`'s own declared thresholds — the same file
# `aistack.cli.runtime_diagnose.DEFAULT_BACKUP_THRESHOLDS` reads,
# declared again here for the same reason `DEFAULT_STORAGE_THRESHOLDS`
# is: no CLI in this package imports another. Unlike
# `DEFAULT_STORAGE_THRESHOLDS`'s own loading function
# (`storage_thresholds_for_host`, imported above rather than
# duplicated a third time), there was never a duplicated
# `backup_thresholds` function here to begin with — `backup_thresholds
# _for_host` (`aistack.providers.filesystem.thresholds`) has been the
# only implementation from the start, imported by both CLIs alike.
DEFAULT_BACKUP_THRESHOLDS = (
    Path(__file__).resolve().parents[1]
    / "providers"
    / "filesystem"
    / "definitions"
    / "backup_thresholds.yml"
)

# `OPS-0007`'s own declared thresholds — the same file
# `aistack.cli.runtime_diagnose.DEFAULT_GPU_THRESHOLDS` reads, declared
# again here for the same reason `DEFAULT_BACKUP_THRESHOLDS` is: no CLI
# in this package imports another.
DEFAULT_GPU_THRESHOLDS = (
    Path(__file__).resolve().parents[1]
    / "providers"
    / "gpu"
    / "definitions"
    / "gpu_thresholds.yml"
)

# `OPS-0008`'s own declared health-score weights. Not scoped by host,
# unlike the three `DEFAULT_*_THRESHOLDS` above: a health score weighs
# whichever domains this host's own cockpit instruments, but the
# weight a domain costs is the same wherever this runs.
DEFAULT_HEALTH_SCORE_WEIGHTS = (
    Path(__file__).resolve().parents[1]
    / "health"
    / "definitions"
    / "health_score_weights.yml"
)

# `OPS-0009`'s own declared PRA test records — not scoped by host, the
# same reason `DEFAULT_HEALTH_SCORE_WEIGHTS` is not: a restore test is
# a fleet-wide fact the owner records by hand, not a threshold that
# varies by which host renders the page.
DEFAULT_PRA_TESTS = (
    Path(__file__).resolve().parents[1] / "pra" / "definitions" / "pra_tests.yml"
)

# `OPS-0010`'s own declared backup-strategy records — not scoped by
# host, the same reason `DEFAULT_PRA_TESTS` is not: which engine (if
# any) covers a service's persistent state is a fleet-wide fact the
# owner records by hand, not a threshold that varies by which host
# renders the page.
DEFAULT_BACKUP_STRATEGY = (
    Path(__file__).resolve().parents[1]
    / "backup_strategy"
    / "definitions"
    / "backup_strategy.yml"
)

# The same file `aistack.cli.architecture_render.DEFAULT_CATEGORIZATION`
# reads — declared again here rather than imported, the same "no CLI
# in this package imports another" convention every other `DEFAULT_*`
# constant in this module already holds.
DEFAULT_CATEGORIZATION = (
    Path(__file__).resolve().parents[1]
    / "architecture"
    / "definitions"
    / "service_categorization.yml"
)

# `network_docker_discover.py`'s own output path — the last observation
# it wrote, read here rather than collected live: that command is
# never triggered automatically (`NetworkDockerDiscoveryProvider`'s own
# docstring, decided with the owner 2026-09-12), so this domain reads
# whatever it last found, exactly like every other `reports/generated/`
# artifact this heritage reads back rather than regenerates on render.
# A plain `Path("reports/generated/...")`, the same cwd-relative
# convention `network_docker_discover.main` itself already uses for
# this exact file, not the `Path(__file__).resolve()`-relative
# convention the constants above hold — this one names an *output*,
# not a shipped definition.
DEFAULT_NETWORK_DOCKER_OBSERVATION = Path(
    "reports/generated/network-docker-observation.json"
)

# R10, 2026-09-30 — resolves the Troubleshooting Assistant's own LAN
# address for `render_html`'s new `troubleshooting_base_url`
# parameter (see that function's own docstring), the exact same
# convention `aistack.cli.console_render.DEFAULT_INSTANCE_CONFIG`
# already uses for its own `console_links.yml` `service:` entries —
# declared explicitly here rather than left to a loader's own internal
# fallback, the same reasoning that module's own comment gives.
DEFAULT_INSTANCE_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "instance"
    / "definitions"
    / "instance_config.yml"
)

# `PLAN-J7` § 1 (`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`): the
# domain vocabulary the owner named before any code — "stockage,
# services, backup/PRA, GPU" — not this module's own invention, closed
# at four from 2026-09-11 until `PLAN-J11` § 11.9.1's third and last
# named gap ("tests PRA") reopened it to five, on the owner's own
# explicit decision, 2026-09-23. All five reference cases have since
# named a domain (Storage `PLAN-J7` § 6, Services § 8, Sauvegarde/PRA
# § 9, GPU § 10, Tests PRA — `OPS-0009`, 2026-09-23) — this note stays
# declared for a host where a domain's own check still reports nothing
# to observe (no threshold file, no `nvidia-smi`, Docker unreachable,
# no PRA test definition), never a false "healthy" (`FDN-0003` Article
# 12).


def storage_domain(hostname: str) -> HealthDomain:
    """
    `PLAN-J7` § 6's own domain, built from the same primitives
    `aistack.cli.runtime_diagnose` already wires into its own report:
    `storage_thresholds_for_host` narrows the fleet-wide file to this
    host, `StorageProvider` reads it, `find_storage_shortage` decides
    which mounts crossed `OPS-0005`, `evaluate_storage` states the
    finding. A host with nothing declared, or a missing/unreadable
    definition, is `instrumented=False` with the same note
    `storage_thresholds_for_host` already names — the same absence,
    stated the same way, whichever command asks.
    """

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
    """
    `PLAN-J7` § 8's own domain: `OPS-0004`'s third reference incident
    (restart loops / unhealthy containers after a power outage),
    detected the same instantaneous-only way `find_container_distress`
    documents — no config file to be missing, unlike storage: Docker
    is either observable from this host or it is not, and that is
    what the note names when it is not.

    **GIGABYTE only, by construction, not by a declared scope check
    here.** `DockerProvider` talks to whatever `docker` binary is on
    the machine this process runs on — there is no Docker provider for
    the Raspberry (a limitation `PLAN-J2` already documented), so
    running this on any host without a reachable Docker daemon —
    the Raspberry included — reads as not instrumented, the same
    honest absence storage already shows on a host with nothing
    declared for it.
    """

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
    """
    `PLAN-J7` § 9's own domain: `OPS-0004`'s fourth reference case —
    the owner's own stated requirement to verify a backup actually
    exists, is functional, and is not too old. Built from the same
    primitives `aistack.cli.runtime_diagnose` already wires into its
    own report: `backup_thresholds_for_host` narrows the fleet-wide
    file to this host, `BackupProvider` reads it, `find_backup_gaps`
    decides which paths are missing or stale against `OPS-0006`,
    `evaluate_backup` states the finding.

    Existence and freshness only (the owner's chosen v1 scope,
    2026-09-11) — periodic restore tests and documentation currency
    are named out of scope, `OPS-0006` § *Out of scope*. A host with
    nothing declared, or a missing/unreadable definition, is
    `instrumented=False` with the same note `backup_thresholds_for_host`
    already names — the same absence, stated the same way, whichever
    command asks.
    """

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
    """
    `PLAN-J7` § 10's own domain: `OPS-0004`'s fifth reference case —
    the owner's own stated requirement to verify GPU delegation and
    monitor the CPU/GPU duo's consumption. Built from the same
    primitives `aistack.cli.runtime_diagnose` already wires into its
    own report: `gpu_thresholds_for_host` narrows the fleet-wide file
    to this host, `NvidiaGpuProvider` reads it, `find_gpu_anomalies`
    decides which readings crossed `OPS-0007`, `evaluate_gpu` states
    the finding.

    Consumption monitoring only (the owner's chosen v1 scope,
    2026-09-11) — per-service delegation verification is named out of
    scope, `OPS-0007` § *Out of scope*. A host with nothing declared,
    or a missing/unreadable definition, is `instrumented=False` with
    the same note `gpu_thresholds_for_host` already names — the same
    absence, stated the same way, whichever command asks. A host with
    thresholds declared but no `nvidia-smi` reading anything (no card,
    no driver) reads as instrumented with nothing to report — the same
    "declared but currently clean" state every other domain already
    allows, since `find_gpu_anomalies` on an empty reading tuple
    produces no anomaly.
    """

    thresholds, note = gpu_thresholds_for_host(DEFAULT_GPU_THRESHOLDS, hostname)

    if not thresholds:
        return HealthDomain(name="GPU", instrumented=False, note=note)

    readings = NvidiaGpuProvider().collect_readings()
    anomalies = find_gpu_anomalies(readings, thresholds)

    return HealthDomain(name="GPU", instrumented=True, findings=evaluate_gpu(anomalies))


def pra_tests_domain() -> HealthDomain:
    """
    `PLAN-J11` § 11.9.1's third and last named gap ("tests PRA"),
    reopened and closed 2026-09-23: `OPS-0004`'s reopened requirement
    to demonstrate, on a real cadence, that a restore actually works —
    not only that a backup file exists (`Sauvegarde / PRA`'s own v1
    scope, unchanged). `load_pra_tests_yaml` reads `OPS-0009`'s
    declared record of every service the owner tests and each one's
    own last-known outcome, `find_pra_test_gaps` decides which
    services are untested, stale, or already recorded as failed
    against `OPS-0009`'s declared threshold, `evaluate_pra_tests`
    states the finding.

    **Not host-scoped, unlike every other domain function here.** A
    restore test is a fleet-wide fact the owner records by hand, not
    a per-host observation `StorageProvider`/`DockerProvider`/
    `NvidiaGpuProvider` each collect from the machine this process
    happens to run on — so this domain reads the same result
    wherever `main()` runs, the same way `DEFAULT_PRA_TESTS` is not
    scoped by host either.

    A missing or unreadable definition is `instrumented=False` with a
    note naming why — the same absence, stated the same way, every
    other domain already holds for its own declared file.

    **Since 1.6 tranche 4 (R9, 2026-09-30, `OPS-0004`'s eighth
    reference case)**: `find_undeclared_pra_tests` also compares
    `OPS-0010`'s own declared stateful services (`backup_strategy.yml`,
    `has_state: true`) against the set `pra_tests.yml` actually names,
    citing the ones missing entirely as `NOT_DECLARED`. Unlike
    `DEFAULT_PRA_TESTS`, `DEFAULT_BACKUP_STRATEGY` is optional here,
    the same "supplementary, best-effort" role
    `network-docker-observation.json` already plays for `inventory_gap
    _domain`: its absence or corruption narrows this render to the
    three reasons `find_pra_test_gaps` alone already detects, never
    making the whole domain `instrumented=False` over a second file
    this check alone needs.
    """

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
    """
    1.6 tranche 2's own domain (R9, 2026-09-30): `OPS-0004`'s sixth
    reference case — every stateful service already named in this
    session's real PRA history, confronted against the backup engine
    (if any) actually confirmed to cover it. `load_backup_strategy_yaml`
    reads `OPS-0010`'s declared record, `find_uncovered_state` decides
    which declared services hold state with no known engine,
    `evaluate_uncovered_state` states the finding.

    **Not host-scoped, the same reason `pra_tests_domain` is not.** A
    backup strategy declaration is a fleet-wide fact the owner records
    by hand, not a per-host observation a live Provider collects from
    the machine this process happens to run on.

    A missing or unreadable definition is `instrumented=False` with a
    note naming why — the same absence, stated the same way, every
    other domain already holds for its own declared file.
    """

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
    """
    1.6 tranche 3's own domain (R9, 2026-09-30): `OPS-0004`'s seventh
    reference case — `service_categorization.yml`'s own declared
    containers, joined against what is actually found running.
    `load_service_categorization_yaml` reads the declared inventory,
    `DockerRuntimeCatalogBuilder`/`DockerProvider` observe this host's
    own containers live, `network_docker_discover`'s last observation
    (if any) adds every other LAN host it last found, `find_inventory_
    gaps` decides which containers are declared nowhere or found
    nowhere, `evaluate_inventory_gap` states the finding.

    **A missing or unreadable `service_categorization.yml` is
    `instrumented=False`** — the same absence, stated the same way,
    every other domain already holds for its own declared file. A
    missing or unreadable `network-docker-observation.json` is *not*
    the same kind of absence: that file is optional, best-effort,
    supplementary data (`network_docker_discover` "only runs when
    invoked explicitly" — most renders will not have a fresh one) —
    its absence silently narrows this domain to a local-only
    reconciliation rather than declaring the whole domain
    uninstrumented over a file nothing here requires to exist.
    """

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
        # The same tolerant absence `services_domain` already holds for
        # an unreachable local Docker daemon — local containers are
        # simply not added, never treated as "none exist".
        discovered = {}

    if DEFAULT_NETWORK_DOCKER_OBSERVATION.exists():
        try:
            observation = json.loads(
                DEFAULT_NETWORK_DOCKER_OBSERVATION.read_text(encoding="utf-8")
            )
            discovered.update(discovered_containers_from_network_observation(observation))
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
    cockpit: HealthCockpit, weights: HealthScoreWeights | None
) -> tuple[TechnicalDebtScore | None, str]:
    """
    `PLAN-J11` § 11.9.1's "dette technique scorée" gap, closed
    2026-09-23: a dedicated card, not a fifth `HealthDomain` —
    `OPS-0004/technical-debt` is a qualification any of the four
    domains' own `evaluate_*` may already cite (so far Services,
    Sauvegarde/PRA and GPU each do, on their own reference incidents),
    not a fifth thing to instrument. Findings are gathered from every
    domain in `cockpit`, not only Services — the owner's real case
    (containers stuck after a power outage) is Services', but
    restricting this card to that one domain would silently miss a
    stale backup or a hot GPU already carrying the same qualification,
    the same `FDN-0003` Article 12 discipline every other honest count
    in this package already holds.

    `weights.for_domain("Services")` is `OPS-0008`'s own declared
    weight for the Services domain, reused rather than a new weight
    declared for this card — the owner's own choice, 2026-09-23 ("même
    poids que le domaine Services actuel"). `weights is None` (no
    declared weights file at all) is the same honest absence
    `compute_health_score` is never even reached for; a declared file
    missing a "Services" entry is instead the same configuration
    defect `compute_health_score` itself raises on, since `OPS-0008`
    is expected to cover the domain this card reuses.

    Two-branch return, mirroring `health_score_weights`'s own shape:
    `(None, note)` when nothing can be computed, `(score, "")` when it
    can — the same idiom `_render_score`/`_render_technical_debt`
    already read to decide between a real score and a stated absence.
    """

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


def main() -> None:
    """
    `PLAN-J7` § 6.4/6.5/§ 11: the cockpit visuel, now scored.
    `render findings first, decide the score model once there is
    something real to weigh` was the owner's own sequencing
    (2026-09-11) — four domains were instrumented and confirmed on
    GIGABYTE before `OPS-0008` declared a single weight, so the score
    this prints is never earlier than the findings it is built from.

    **Also writes the "Dette technique" card, added 2026-09-23**
    (`PLAN-J11` § 11.9.1) — computed from the same cockpit and the
    same `OPS-0008` weights the health score already reads, never a
    second load of either.

    **Also resolves the Troubleshooting Assistant's own LAN address,
    added 2026-09-30** — the owner's own "Élargir + relier" cadrage:
    every finding this page shows should link into that assistant's
    guided `reason`/`explain`/`recommend` chain. Resolved once, from
    the declared instance config, the same `service_url(...)` call
    `console_render.py` already makes for its own links — `None` (the
    v1 shape every call before this existed) if that config is
    missing or unreadable, which renders every finding exactly as
    before rather than failing the whole page over one optional link.
    """

    cockpit = build_cockpit(socket.gethostname())

    weights, score_note = health_score_weights(DEFAULT_HEALTH_SCORE_WEIGHTS)
    score = compute_health_score(cockpit, weights) if weights is not None else None
    debt_score, debt_score_note = technical_debt_score(cockpit, weights)

    try:
        troubleshooting_base_url: str | None = load_instance_config_yaml(
            DEFAULT_INSTANCE_CONFIG
        ).service_url("troubleshooting_assistant_ui")
    except (ValueError, OSError):
        # Optional, best-effort — the same tolerant absence every
        # other `DEFAULT_*` definition in this module already holds
        # for its own file: a missing or unreadable instance config
        # narrows this render to no "Diagnostiquer" button anywhere,
        # never a failed page.
        troubleshooting_base_url = None

    # ADR-0010 § 5 (2026-09-27): one page per declared language, the
    # reference keeping `health.html` and its history stream. The
    # cockpit is built once — the host does not change with the
    # language it is read in.
    languages = default_languages()
    generated_dir = Path("reports/generated")
    output_path = generated_dir / "health.html"

    for language in languages.available:
        written = HealthHtmlArtifactGenerator().generate(
            cockpit=cockpit,
            output_path=page_file(
                generated_dir, "health.html", language.code, languages.reference
            ),
            score=score,
            score_note=score_note,
            technical_debt_score=debt_score,
            technical_debt_note=debt_score_note,
            lang=language.code,
            troubleshooting_base_url=troubleshooting_base_url,
        )

        if language.code == languages.reference:
            output_path = written

    if score is not None:
        print(
            f"Health cockpit written to {output_path} "
            f"(score: {score.value}/100, {score.bucket}, "
            f"{score.measured_domains}/{score.total_domains} domain(s) measured)"
        )
    else:
        print(f"Health cockpit written to {output_path} (score: {score_note})")

    if debt_score is not None:
        print(
            f"Technical-debt score: {debt_score.value}/100, {debt_score.bucket}, "
            f"{len(debt_score.findings)} finding(s)"
        )
    else:
        print(f"Technical-debt score: {debt_score_note}")


if __name__ == "__main__":
    main()
