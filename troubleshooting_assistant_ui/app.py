from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path
from typing import NamedTuple
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from aistack.ai_runtime.ollama_engine import OllamaEngine
from aistack.ai_runtime.operations import explain, reason, recommend
from aistack.ai_runtime.reasoning_history import record_ai_reasoning
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.instance.yaml import load_instance_config_yaml
from aistack.pra.yaml import load_pra_tests_yaml
from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    ResourcePriorityDefinition,
)
from aistack.priority.yaml import (
    load_resource_priority_yaml,
    save_resource_priority_yaml,
)
from aistack.providers.docker import DockerProvider
from aistack.providers.filesystem import (
    BackupProvider,
    StorageProvider,
    backup_thresholds_for_host,
    storage_thresholds_for_host,
)
from aistack.providers.gpu import NvidiaGpuProvider, gpu_thresholds_for_host
from aistack.providers.host.provider import HostProvider
from aistack.providers.repository import RepositoryProvider
from aistack.runtime.backup_gap import find_backup_gaps
from aistack.runtime.container_distress import find_container_distress
from aistack.runtime.evaluate import evaluate
from aistack.runtime.evaluate_backup import evaluate_backup
from aistack.runtime.evaluate_gpu import evaluate_gpu
from aistack.runtime.evaluate_inventory_gap import evaluate_inventory_gap
from aistack.runtime.evaluate_pra_tests import evaluate_pra_tests
from aistack.runtime.evaluate_services import evaluate_services
from aistack.runtime.restart_loop import restart_loop_findings
from aistack.runtime.evaluate_storage import evaluate_storage
from aistack.runtime.evaluate_uncovered_state import evaluate_uncovered_state
from aistack.runtime.gpu_anomaly import find_gpu_anomalies
from aistack.runtime.idle_consumption import find_unexplained_consumption
from aistack.runtime.inventory_gap import (
    discovered_containers_from_network_observation,
    find_inventory_gaps,
)
from aistack.runtime.pra_test_gap import find_pra_test_gaps, find_undeclared_pra_tests
from aistack.runtime.storage_shortage import find_storage_shortage
from aistack.runtime.uncovered_state_gap import find_uncovered_state

# A guided, step-by-step GUI over J8's own real chain — the new
# milestone the owner asked for on closing J8 itself (2026-09-18,
# `claude/PLAN-TROUBLESHOOTING-ASSISTANT-UI-2026-09-18.md`):
# "créer un nouveau jalon pour la partie GUI... une sorte de chatbot
# interactif... pour le guider en mode pas à pas." Scoped v1,
# confirmed by the owner: pannes réelles seulement (not a general
# AIStack assistant), one structured choice at a time (not free-form
# chat), a new dedicated FastAPI mini-app (same family as
# `priority_ui`/`selection_ui`/`network_discovery_ui`), LAN-only.
#
# **`qualified_findings()` below is duplicated from
# `aistack.cli.ai_reason`, not imported** — the same choice
# `aistack.cli.ai_reason.qualified_findings` itself documents against
# `aistack.cli.runtime_diagnose` ("no CLI in this package imports
# another"), extended one step further here: no UI app in this
# heritage imports a CLI module either (`priority_ui`/`selection_ui`/
# `network_discovery_ui` all import only from non-CLI packages —
# `aistack.priority`, `aistack.selection`, `aistack.network_discovery`
# — never from `aistack.cli`). A drift-guard test is not possible
# here the way `test_ai_reason.py` holds one against
# `runtime_diagnose.py`: both of those are plain modules pytest can
# import, but `fastapi` is deliberately outside the governed venv
# (decision #9, 2026-08-29), so this file cannot be imported by the
# governed test suite at all — the same reason
# `priority_ui`/`selection_ui`/`network_discovery_ui` carry no test
# file for their own `app.py`. Verified only by real execution
# against GIGABYTE, the same way those three already are.
#
# **`/finding/{subject}/apply` (2026-09-18)** — the owner's own
# follow-up once the guided read-only flow above worked end to end:
# "fait un diagnostic, mais ne propose pas de mécanisme de
# correction." Scoped through a second governance interview to
# exactly one fixed, code-known, hand-written action — classing a
# subject as a `background` container via the already-in-production
# `save_resource_priority_yaml` (`priority_ui/app.py`'s own `/save`
# writes the same field) — never anything derived from the AI's own
# `recommend` text, and never the broader `priority` classification,
# which needs real judgement (a detector type, CPU thresholds) a
# single click cannot safely default. See `apply()`'s own docstring
# below for the full scoping and why the verification after saving
# is a second real diagnosis, not an assumption.
#
# **`qualified_findings()` widened to the full Cockpit Santé,
# 2026-09-30** — the owner, reading the real console
# (`aistack.persiaut-family.fr/console.html`): "les findings en rouge
# doivent être cliquables et doivent diriger vers une explication en
# français... avec la possibilité de résoudre le problème de façon
# accompagnée par les modules d'IA." Cadré through a governance
# interview, "Élargir + relier" confirmed: every domain
# `aistack.cli.health_render.build_cockpit` already assembles
# (Stockage, Services, Sauvegarde/PRA, GPU, Tests PRA, État
# persistant, Écarts d'inventaire) now reaches this assistant's own
# `reason`/`explain`/`recommend` chain, not only the original CPU/
# consumption check. `build_cockpit` and its seven domain-builder
# functions are duplicated below from `aistack.cli.health_render`,
# not imported — the same "no UI app imports a CLI module" choice
# this docstring already states above, applied a third time
# (`aistack.cli.console_render` already duplicates the same seven
# functions for its own console cartouche). **Explicitly not
# merged** with `/finding/.../apply`'s own one-click "classer en
# background" scope, confirmed unchanged in the same interview: that
# route stays reserved to its original, narrowly-cadred CPU/
# consumption action — see `_APPLYABLE_DOMAINS` and `apply()`'s own
# docstring below for how the six new domains are kept out of it, and
# `QualifiedFinding.key` below for why a real subject collision
# across domains (confirmed 2026-09-30: "gigabyte", "nextcloud" and
# "immich" are each flagged today by both Tests PRA and État
# persistant) cannot simply route on `finding.subject` alone.
REPO_ROOT = Path(__file__).resolve().parents[1]
repository = RepositoryProvider(REPO_ROOT)

RESOURCE_PRIORITY_PATH = repository.resolve(
    "src/aistack/priority/definitions/resource_priority.yml"
)
AI_RUNTIME_PATH = repository.resolve(
    "src/aistack/ai_runtime/definitions/ai_runtime.yml"
)

# The seven `DEFAULT_*` paths `build_cockpit` below needs — mirrors
# `aistack.cli.health_render`'s own constants exactly (same files,
# same "no CLI imports another" convention), expressed through this
# file's own `repository.resolve("src/aistack/...")` idiom rather
# than `health_render.py`'s `Path(__file__).resolve().parents[1] /
# ...` — the two resolve to the same absolute path, since `__file__`
# sits one directory deeper there (`src/aistack/cli/`) than
# `REPO_ROOT` does here.
DEFAULT_STORAGE_THRESHOLDS = repository.resolve(
    "src/aistack/providers/filesystem/definitions/storage_thresholds.yml"
)
DEFAULT_BACKUP_THRESHOLDS = repository.resolve(
    "src/aistack/providers/filesystem/definitions/backup_thresholds.yml"
)
DEFAULT_GPU_THRESHOLDS = repository.resolve(
    "src/aistack/providers/gpu/definitions/gpu_thresholds.yml"
)
DEFAULT_PRA_TESTS = repository.resolve("src/aistack/pra/definitions/pra_tests.yml")
DEFAULT_BACKUP_STRATEGY = repository.resolve(
    "src/aistack/backup_strategy/definitions/backup_strategy.yml"
)
DEFAULT_CATEGORIZATION = repository.resolve(
    "src/aistack/architecture/definitions/service_categorization.yml"
)

# Mirrors `aistack.cli.health_render.DEFAULT_NETWORK_DOCKER_OBSERVATION`
# in what it names, but not in how it is anchored: both CLIs resolve
# this cwd-relative (they are only ever invoked from the repository
# root by the scripts that call them), while every other path in this
# file — a systemd/uvicorn service whose own working directory is not
# guaranteed the same way — is deliberately `repository.resolve`-
# anchored instead. This file's own convention wins here; the
# observation itself stays optional/best-effort either way.
DEFAULT_NETWORK_DOCKER_OBSERVATION = repository.resolve(
    "reports/generated/network-docker-observation.json"
)

app = FastAPI(title="AIStack Troubleshooting Assistant")
templates = Jinja2Templates(
    directory=str(repository.resolve("troubleshooting_assistant_ui/templates"))
)

# R10, 2026-09-30 — the direct LAN link back to the console, resolved
# from the declared instance config instead of hand-typed in three
# separate templates (`index.html`, `step.html`, `applied.html`) —
# same fix as `network_discovery_ui`'s own.
INSTANCE_CONFIG_PATH = repository.resolve(
    "src/aistack/instance/definitions/instance_config.yml"
)
CONSOLE_BASE_URL = load_instance_config_yaml(INSTANCE_CONFIG_PATH).service_url(
    "console"
)

# One in-memory session per finding, keyed by `QualifiedFinding.key`
# (below) rather than by the bare `RuntimeFinding.subject` since
# 2026-09-30's widening — deliberately not persisted: this screen is a
# LAN-only, single-owner guide over answers
# `aistack.ai_runtime.reasoning_history` already persists durably the
# moment `/start` computes them (see below). Restarting this process
# (or the owner opening the same finding a second time) simply
# recomputes it — a fresh Ollama round-trip, not a lost fact, since
# the earlier entry stays in
# `reports/generated/ai-reasoning/<subject>.json`'s own history (keyed
# there by the real subject, never by this route's own key).
_SESSIONS: dict[str, dict[str, object]] = {}

_STEP_COUNT = 4
_OPERATION_BY_STEP: dict[int, str] = {2: "reason", 3: "explain", 4: "recommend"}


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


def _language(request: Request) -> PageLanguage:
    """
    ADR-0010: the language this request is answered in — `?lang=` (the
    console hands it over in its link), then this host's own cookie,
    then the reference. Tested in `aistack.i18n.web`, not here.

    **The AI Runtime's answers now follow it too (2026-09-27),
    corrected from the original ADR-0010 § Open Points design**: this
    same language is passed to `reason`/`explain`/`recommend` as their
    own `target_language` in `start()` below, with a translation pass
    enforcing it whenever it is not English (`aistack.ai_runtime
    .operations`'s own docstring names why "the interface follows it,
    the model's own answer does not" turned out to be the wrong fix —
    the model did not reliably answer in French either, whatever the
    interface said).
    """

    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
    )


def _render(request: Request, name: str, context: dict[str, object]) -> HTMLResponse:
    language = _language(request)
    response = templates.TemplateResponse(
        request=request,
        name=name,
        context={
            **context,
            **language.context(),
            "console_base_url": CONSOLE_BASE_URL,
        },
    )

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response


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

    definition, note = resource_priority_definition(RESOURCE_PRIORITY_PATH)

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

    thresholds, note = backup_thresholds_for_host(DEFAULT_BACKUP_THRESHOLDS, hostname)

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
            item.id: None for item in docker_catalog.items if item.kind == "container"
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
_APPLYABLE_DOMAINS = frozenset({CONSUMPTION_DOMAIN})


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
        return self.domain in _APPLYABLE_DOMAINS


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

    subject_counts: dict[str, int] = {}
    for _, finding in tagged:
        subject_counts[finding.subject] = subject_counts.get(finding.subject, 0) + 1

    qualified = tuple(
        QualifiedFinding(
            key=(
                finding.subject
                if subject_counts[finding.subject] == 1
                else f"{domain_name}::{finding.subject}"
            ),
            domain=domain_name,
            finding=finding,
        )
        for domain_name, finding in tagged
    )

    return qualified, note


@app.get("/aide", response_class=HTMLResponse)
def aide(request: Request):
    """
    A hand-written help page — how to open a terminal, find
    GIGABYTE on the LAN, connect over SSH, and paste a command.
    Owner's request (2026-09-18): non-technical readers following a
    finding's declared remediation need this, and it is fixed,
    verified content, never AI-generated per finding — the owner's
    own explicit choice, to avoid a model inventing a command that
    does not match the real remediation (GOV-P-001).
    """

    return _render(request, "aide.html", {})


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    findings, note = qualified_findings()

    return _render(
        request,
        "index.html",
        {
            "findings": findings,
            "note": note,
            "status": request.query_params.get("status"),
        },
    )


@app.post("/finding/{key}/start")
def start(request: Request, key: str):
    """
    Computes `reason`/`explain`/`recommend` together, over the real,
    freshly re-collected finding routed by `key` — exactly the same
    three calls `aistack.cli.ai_reason.main()` makes in its own loop
    body — records them as one combined entry (J7's own decision #2,
    `claude/PLAN-J7-AI-REASONING-HISTORY-2026-09-18.md`) immediately,
    before showing a single step: traceability does not wait on
    whether the owner clicks all the way through the wizard.

    `key` is `QualifiedFinding.key` (module docstring above), not
    always `finding.subject` — the lookup below matches on it, but
    everything recorded (`record_ai_reasoning`, the session, the AI
    prompts inside `reason`/`explain`/`recommend`) uses the real
    `finding.subject` beneath it, never this routing key.
    """

    findings, _ = qualified_findings()
    entry = next((f for f in findings if f.key == key), None)

    if entry is None:
        status = _language(request).t("troubleshooting.status.not_found", subject=key)
        return RedirectResponse(f"/?status={quote(status)}", status_code=303)

    finding = entry.finding

    ai_runtime_definition = load_ai_runtime_yaml(AI_RUNTIME_PATH)
    target_language = _language(request).lang

    # Built even when `model` is empty — same note
    # `aistack.cli.ai_reason.main()` already carries for the same
    # construction.
    engine = OllamaEngine(
        host=ai_runtime_definition.host,
        port=ai_runtime_definition.port,
        model=ai_runtime_definition.model or "",
    )

    # A second engine, a second (fast) model — never `engine` again —
    # asked to translate into `target_language` whenever it is not
    # English (`aistack.ai_runtime.operations`'s own docstring,
    # 2026-09-27). `None` when the owner has not declared
    # `translator_model:` yet: every answer then travels exactly as
    # it did before this feature existed, the same "nothing is asked
    # for unconfirmed" guard `engine` itself already gets above.
    translator = (
        OllamaEngine(
            host=ai_runtime_definition.host,
            port=ai_runtime_definition.port,
            model=ai_runtime_definition.translator_model,
        )
        if ai_runtime_definition.translator_model
        else None
    )

    answers: tuple[AIRuntimeAnswer, AIRuntimeAnswer, AIRuntimeAnswer] = (
        reason(
            finding, engine, ai_runtime_definition.model,
            target_language=target_language, translator=translator,
        ),
        explain(
            finding, engine, ai_runtime_definition.model,
            target_language=target_language, translator=translator,
        ),
        recommend(
            finding, engine, ai_runtime_definition.model,
            target_language=target_language, translator=translator,
        ),
    )

    record_ai_reasoning(finding, answers)

    _SESSIONS[key] = {
        "finding": finding,
        "domain": entry.domain,
        "applyable": entry.applyable,
        "answers": {
            "reason": answers[0],
            "explain": answers[1],
            "recommend": answers[2],
        },
    }

    return RedirectResponse(f"/finding/{quote(key)}/step/1", status_code=303)


@app.get("/finding/{key}/step/{step}", response_class=HTMLResponse)
def step(request: Request, key: str, step: int):
    session = _SESSIONS.get(key)

    if session is None or step < 1 or step > _STEP_COUNT:
        status = _language(request).t("troubleshooting.status.expired", subject=key)
        return RedirectResponse(f"/?status={quote(status)}", status_code=303)

    operation = _OPERATION_BY_STEP.get(step)
    answers = session["answers"]
    assert isinstance(answers, dict)
    answer = answers[operation] if operation else None
    finding = session["finding"]
    assert isinstance(finding, RuntimeFinding)

    return _render(
        request,
        "step.html",
        {
            "key": key,
            "subject": finding.subject,
            "domain": session["domain"],
            "applyable": session["applyable"],
            "step": step,
            "total_steps": _STEP_COUNT,
            "finding": finding,
            "answer": answer,
        },
    )


@app.post("/finding/{key}/apply")
def apply(request: Request, key: str):
    """
    Applies the one, single-click-safe fix this assistant knows how
    to make: declaring the finding's real `subject` a background
    container in the governed resource-priority definition — exactly
    the write `priority_ui/app.py`'s own `/save` route already
    performs in production (`save_resource_priority_yaml`), scoped
    here to one container instead of a full-form rewrite.

    Owner's request (2026-09-18): "déclenche une panne facile à
    corriger... on vérifie que la correction est proposée, qu'on peut
    l'appliquer et qu'elle corrige effectivement le problème."
    Answered through a 3-question governance interview, all three
    "recommandé":

    - **Scope: "background" only, v1.** Never "priority" — that
      needs a detector type and CPU thresholds, a real judgement call
      a single click cannot safely default (unlike `priority_ui`'s
      own `/save`, which asks the owner for those values explicitly
      in the form before writing them).
    - **Never the AI's own `recommend` text turned into an action.**
      This route performs exactly one fixed, code-known,
      hand-written write — never anything parsed or derived from
      `answer.response`. The `recommend` step's own suggestion stays
      a suggestion (GOV-P-001, ARC-P-012); this button is a
      *separate*, explicitly-confirmed action the owner triggers with
      its own click, not the recommendation being carried out on its
      own.
    - **Verified, not assumed.** `find_unexplained_consumption`
      (`aistack.runtime.idle_consumption`) flags a container purely
      because it is absent from both `priority` and `background` —
      the moment this write declares it, the next `evaluate()` no
      longer reports the finding at all, with no dependency on the
      resource-priority monitor's own throttling loop having run
      yet. This route re-runs `qualified_findings()` immediately
      after saving and reports plainly whether the subject's finding
      is actually gone — never claims success without checking.

    **Domain guard, added with 2026-09-30's widening, confirmed
    unchanged in the same governance interview**: this route stays
    reserved to `CONSUMPTION_DOMAIN` findings alone — the six cockpit
    domains `qualified_findings()` now also surfaces get no auto-
    correction invented for them here. Enforced twice: `step.html`
    hides this button whenever `applyable` is false, and this route
    itself refuses the same way on a direct POST that skips the UI —
    a template-only guard is not enough, `FDN-0003`'s own "verify,
    don't assume" discipline applies to this route's own reachability
    too, not only to its outcome.
    """

    t = _language(request).t
    session = _SESSIONS.get(key)

    if session is None or not session.get("applyable"):
        status = t("troubleshooting.status.not_applyable", subject=key)
        return RedirectResponse(f"/?status={quote(status)}", status_code=303)

    finding = session["finding"]
    assert isinstance(finding, RuntimeFinding)
    subject = finding.subject

    definition, note = resource_priority_definition(RESOURCE_PRIORITY_PATH)

    if definition is None:
        session["applied"] = {"outcome": "error", "message": note}
        return RedirectResponse(f"/finding/{quote(key)}/applied", status_code=303)

    already_priority = any(
        app_def.container == subject for app_def in definition.priority
    )
    already_background = any(
        container.name == subject
        for container in definition.background.containers
    )

    if already_priority:
        session["applied"] = {
            "outcome": "refused",
            "message": t("troubleshooting.message.already_priority", subject=subject),
        }
        return RedirectResponse(f"/finding/{quote(key)}/applied", status_code=303)

    if already_background:
        action_message = t(
            "troubleshooting.message.already_background", subject=subject
        )
    else:
        updated = ResourcePriorityDefinition(
            priority=definition.priority,
            background=BackgroundPriorityDefinition(
                default_throttled_cpus=definition.background.default_throttled_cpus,
                containers=tuple(
                    sorted(
                        (
                            *definition.background.containers,
                            ContainerPriorityDefinition(name=subject),
                        ),
                        key=lambda container: container.name,
                    )
                ),
            ),
            unlimited_cpus=definition.unlimited_cpus,
            grace_seconds=definition.grace_seconds,
        )
        save_resource_priority_yaml(updated, RESOURCE_PRIORITY_PATH)
        action_message = t(
            "troubleshooting.message.added",
            subject=subject,
            cpus=updated.background.default_throttled_cpus,
        )

    # Scoped to `CONSUMPTION_DOMAIN` specifically, not just `subject`
    # — the very collision `QualifiedFinding.key`'s own docstring
    # names means a bare `f.subject == subject` match here could pick
    # up a *different* domain's finding that merely shares this
    # subject, and wrongly report this fix as still unresolved (or
    # falsely resolved) over an anomaly it was never meant to touch.
    findings_after, _ = qualified_findings()
    still_present = any(
        entry.domain == CONSUMPTION_DOMAIN and entry.finding.subject == subject
        for entry in findings_after
    )

    session["applied"] = {
        "outcome": "unresolved" if still_present else "resolved",
        "message": action_message,
        "still_present": still_present,
    }

    return RedirectResponse(f"/finding/{quote(key)}/applied", status_code=303)


@app.get("/finding/{key}/applied", response_class=HTMLResponse)
def applied(request: Request, key: str):
    session = _SESSIONS.get(key) or {}
    result = session.get("applied")

    if result is None:
        status = _language(request).t(
            "troubleshooting.status.nothing_applied", subject=key
        )
        return RedirectResponse(f"/?status={quote(status)}", status_code=303)

    finding = session.get("finding")
    subject = finding.subject if isinstance(finding, RuntimeFinding) else key

    return _render(request, "applied.html", {"subject": subject, "result": result})
