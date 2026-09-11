from __future__ import annotations

import socket
import subprocess
from pathlib import Path

from aistack.generators.health import HealthHtmlArtifactGenerator
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.score import compute_health_score
from aistack.health.score_weights import health_score_weights
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
from aistack.runtime.evaluate_services import evaluate_services
from aistack.runtime.evaluate_storage import evaluate_storage
from aistack.runtime.gpu_anomaly import find_gpu_anomalies
from aistack.runtime.storage_shortage import find_storage_shortage

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

# `PLAN-J7` § 1 (`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`): the
# closed domain vocabulary the owner named before any code —
# "stockage, services, backup/PRA, GPU" — not this module's own
# invention. All five reference cases have since named a domain
# (Storage `PLAN-J7` § 6, Services § 8, Sauvegarde/PRA § 9, GPU § 10) —
# this note stays declared for a host where a domain's own check
# still reports nothing to observe (no threshold file, no `nvidia-smi`,
# Docker unreachable), never a false "healthy" (`FDN-0003` Article 12).


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
        name="Services", instrumented=True, findings=evaluate_services(distress)
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


def build_cockpit(hostname: str) -> HealthCockpit:
    return HealthCockpit(
        domains=(
            storage_domain(hostname),
            services_domain(),
            backup_domain(hostname),
            gpu_domain(hostname),
        )
    )


def main() -> None:
    """
    `PLAN-J7` § 6.4/6.5/§ 11: the cockpit visuel, now scored.
    `render findings first, decide the score model once there is
    something real to weigh` was the owner's own sequencing
    (2026-09-11) — four domains were instrumented and confirmed on
    GIGABYTE before `OPS-0008` declared a single weight, so the score
    this prints is never earlier than the findings it is built from.
    """

    cockpit = build_cockpit(socket.gethostname())

    weights, score_note = health_score_weights(DEFAULT_HEALTH_SCORE_WEIGHTS)
    score = compute_health_score(cockpit, weights) if weights is not None else None

    output_path = HealthHtmlArtifactGenerator().generate(
        cockpit=cockpit,
        output_path=Path("reports/generated/health.html"),
        score=score,
        score_note=score_note,
    )

    if score is not None:
        print(
            f"Health cockpit written to {output_path} "
            f"(score: {score.value}/100, {score.bucket}, "
            f"{score.measured_domains}/{score.total_domains} domain(s) measured)"
        )
    else:
        print(f"Health cockpit written to {output_path} (score: {score_note})")


if __name__ == "__main__":
    main()
