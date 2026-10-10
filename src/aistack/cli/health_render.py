from __future__ import annotations

from aistack.config import configured

import json
import socket
import subprocess
from pathlib import Path

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.contracts.health_score import HealthScore, HealthScoreWeights
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.generators.health import HealthHtmlArtifactGenerator
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.hosts.health import hosts_domain
from aistack.data_budget.health import data_budget_domain
from aistack.health.score import compute_health_score
from aistack.health.score_weights import health_score_weights
from aistack.health.plan import debt_plan, health_plan
from aistack.health.technical_debt import compute_technical_debt_score
from aistack.i18n import Languages, default_languages
from aistack.i18n.pages import page_file
from aistack.instance.yaml import load_instance_config_yaml
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
from aistack.renderers.plan.html import PLAN_PAGE, render_plan
from aistack.vigil.snapshot import take as take_snapshot, write as write_snapshot

# Declared thresholds (OPS-0005). No CLI imports another, so each keeps
# its own copy of the paths it needs.
DEFAULT_STORAGE_THRESHOLDS = (
    configured(Path(__file__).resolve().parents[1]
    / "providers"
    / "filesystem"
    / "definitions"
    / "storage_thresholds.yml")
)

# OPS-0006.
DEFAULT_BACKUP_THRESHOLDS = (
    configured(Path(__file__).resolve().parents[1]
    / "providers"
    / "filesystem"
    / "definitions"
    / "backup_thresholds.yml")
)

# OPS-0007.
DEFAULT_GPU_THRESHOLDS = (
    configured(Path(__file__).resolve().parents[1]
    / "providers"
    / "gpu"
    / "definitions"
    / "gpu_thresholds.yml")
)

# Health-score weights (OPS-0008); unlike the thresholds, not scoped by host.
DEFAULT_HEALTH_SCORE_WEIGHTS = (
    configured(Path(__file__).resolve().parents[1]
    / "health"
    / "definitions"
    / "health_score_weights.yml")
)

# PRA test records (OPS-0009): fleet-wide facts, not scoped by host.
DEFAULT_PRA_TESTS = (
    configured(Path(__file__).resolve().parents[1] / "pra" / "definitions" / "pra_tests.yml")
)

# Backup-strategy records (OPS-0010): fleet-wide facts, not scoped by host.
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

# The last output of `network_docker_discover`, which only runs on demand;
# cwd-relative because it is an output, not a shipped definition.
DEFAULT_NETWORK_DOCKER_OBSERVATION = Path(
    "reports/generated/network-docker-observation.json"
)

# Resolves the Troubleshooting Assistant's LAN address.
DEFAULT_INSTANCE_CONFIG = (
    configured(Path(__file__).resolve().parents[1]
    / "instance"
    / "definitions"
    / "instance_config.yml")
)

# The assistant's prefix on the web application's LAN listener
# (ADR-0012, `aistack.web.troubleshooting.PREFIX`).
TROUBLESHOOTING_PATH = "/troubleshooting"

# A domain with nothing to observe on this host (no threshold file, Docker
# unreachable, no definition) is `instrumented=False` with a note, never
# a false "healthy".


def storage_domain(hostname: str) -> HealthDomain:
    """
    Storage: mounts of this host that crossed their OPS-0005 thresholds.

    Not instrumented when this host declares nothing or the file is unreadable.
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
    Services: restarting, unhealthy or crash-looping containers (OPS-0004).

    Uses the local Docker daemon only; a host without one reads as not instrumented.
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
        # Instantaneous state plus restart loops from the docker-events
        # history, which catch a container that reads `running` between crashes.
        findings=evaluate_services(distress) + restart_loop_findings(),
    )


def backup_domain(hostname: str) -> HealthDomain:
    """
    Backup: declared backup paths of this host that are missing or stale (OPS-0006).

    Existence and freshness only; restore tests are `pra_tests_domain`.
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
    GPU: readings that crossed this host's OPS-0007 thresholds.

    Thresholds declared but no `nvidia-smi` reading reads as instrumented and clean.
    """

    thresholds, note = gpu_thresholds_for_host(DEFAULT_GPU_THRESHOLDS, hostname)

    if not thresholds:
        return HealthDomain(name="GPU", instrumented=False, note=note)

    readings = NvidiaGpuProvider().collect_readings()
    anomalies = find_gpu_anomalies(readings, thresholds)

    return HealthDomain(name="GPU", instrumented=True, findings=evaluate_gpu(anomalies))


def pra_tests_domain() -> HealthDomain:
    """
    Restore tests: services untested, stale or failed against OPS-0009.

    Not host-scoped. Also flags covered stateful services of
    `backup_strategy.yml` (OPS-0010) with no restore test at all; that
    file is optional here.
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
    """
    Persistent state: declared stateful services no backup engine covers (OPS-0010).

    Not host-scoped.
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
    Inventory: containers declared in `service_categorization.yml` but not
    found running, or running but not declared.

    Local containers come from Docker; other LAN hosts from the last
    `network_docker_discover` output, which is optional.
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
        # Docker unreachable: local containers are not added.
        discovered = {}

    if DEFAULT_NETWORK_DOCKER_OBSERVATION.exists():
        try:
            observation = json.loads(
                DEFAULT_NETWORK_DOCKER_OBSERVATION.read_text(encoding="utf-8")
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
            hosts_domain(),
            data_budget_domain(),
        )
    )


def technical_debt_score(
    cockpit: HealthCockpit,
    weights: HealthScoreWeights | None,
) -> tuple[TechnicalDebtScore | None, str]:
    """
    Score the technical-debt findings of every domain in `cockpit`.

    Uses the Services weight of OPS-0008. Returns `(None, note)` without
    weights, `(score, "")` otherwise; raises when the weights lack a
    Services entry.
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

    groups = tuple(tuple(domain.findings) for domain in cockpit.domains)

    return compute_technical_debt_score(groups, points), ""


def main() -> None:
    """
    Render the health cockpit, its scores, the action plan and the vigil snapshot.

    The health and technical-debt scores share one cockpit and one load
    of the OPS-0008 weights. Each finding links to the Troubleshooting
    Assistant when the instance config gives its address.
    """

    cockpit = build_cockpit(socket.gethostname())

    weights, score_note = health_score_weights(DEFAULT_HEALTH_SCORE_WEIGHTS)
    score = compute_health_score(cockpit, weights) if weights is not None else None
    debt_score, debt_score_note = technical_debt_score(cockpit, weights)

    try:
        troubleshooting_base_url: str | None = (
            load_instance_config_yaml(DEFAULT_INSTANCE_CONFIG).service_url("web_lan")
            + TROUBLESHOOTING_PATH
        )
    except (ValueError, OSError):
        # Optional: without it, findings get no "Diagnostiquer" button.
        troubleshooting_base_url = None

    # ADR-0010 § 5: one page per declared language from the same cockpit;
    # the reference language keeps `health.html`.
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

    # The vigil compares this render with the one before.
    write_snapshot(
        take_snapshot(
            cockpit,
            score.value if score is not None else None,
            debt_score.value if debt_score is not None else None,
        ),
        generated_dir,
    )

    plan_written = write_plan(
        cockpit,
        weights,
        score=score,
        score_note=score_note,
        debt_score=debt_score,
        debt_note=debt_score_note,
        troubleshooting_base_url=troubleshooting_base_url,
        generated_dir=generated_dir,
        languages=languages,
    )

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

    print(f"Action plan written to {plan_written}")


def write_plan(
    cockpit: HealthCockpit,
    weights: HealthScoreWeights | None,
    *,
    score: HealthScore | None,
    score_note: str,
    debt_score: TechnicalDebtScore | None,
    debt_note: str,
    troubleshooting_base_url: str | None,
    generated_dir: Path,
    languages: Languages,
) -> Path:
    """
    Write `plan.html`, the action plan the score badges open, once per language.

    Written plainly, not with `write_artifact_with_history`: it is a view
    of this run, not a history stream. Returns the reference-language path.
    """

    weight = (weights.for_domain("Services") or 0) if weights is not None else 0
    health = health_plan(cockpit, weights) if weights is not None else ()
    debt = debt_plan(cockpit, weight) if weights is not None else ()
    subject_counts: dict[str, int] = {}
    for domain in cockpit.domains:
        for finding in domain.findings:
            subject_counts[finding.subject] = subject_counts.get(finding.subject, 0) + 1

    reference = generated_dir / PLAN_PAGE
    for language in languages.available:
        path = page_file(generated_dir, PLAN_PAGE, language.code, languages.reference)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(
            render_plan(
                health,
                debt,
                score=score,
                score_note=score_note,
                debt_score=debt_score,
                debt_note=debt_note,
                weight=weight,
                subject_counts=subject_counts,
                troubleshooting_base_url=troubleshooting_base_url,
                lang=language.code,
                languages=languages,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
        if language.code == languages.reference:
            reference = path
    return reference


if __name__ == "__main__":
    main()
