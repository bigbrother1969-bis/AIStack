from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from aistack.ai_runtime.ollama_engine import OllamaEngine
from aistack.ai_runtime.operations import explain, reason, recommend
from aistack.ai_runtime.reasoning_history import record_ai_reasoning
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding
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
from aistack.providers.host.provider import HostProvider
from aistack.providers.repository import RepositoryProvider
from aistack.runtime.evaluate import evaluate
from aistack.runtime.idle_consumption import find_unexplained_consumption

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
REPO_ROOT = Path(__file__).resolve().parents[1]
repository = RepositoryProvider(REPO_ROOT)

RESOURCE_PRIORITY_PATH = repository.resolve(
    "src/aistack/priority/definitions/resource_priority.yml"
)
AI_RUNTIME_PATH = repository.resolve(
    "src/aistack/ai_runtime/definitions/ai_runtime.yml"
)

app = FastAPI(title="AIStack Troubleshooting Assistant")
templates = Jinja2Templates(
    directory=str(repository.resolve("troubleshooting_assistant_ui/templates"))
)

# One in-memory session per finding subject, keyed by subject —
# deliberately not persisted: this screen is a LAN-only, single-owner
# guide over answers `aistack.ai_runtime.reasoning_history` already
# persists durably the moment `/start` computes them (see below).
# Restarting this process (or the owner opening the same finding a
# second time) simply recomputes it — a fresh Ollama round-trip, not
# a lost fact, since the earlier entry stays in
# `reports/generated/ai-reasoning/<subject>.json`'s own history.
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


def qualified_findings() -> tuple[tuple[RuntimeFinding, ...], str]:
    """
    Every `RuntimeFinding` `aistack.runtime.evaluate.evaluate` can
    produce right now, freshly collected — same real subject as
    `aistack.cli.ai_reason.qualified_findings`, duplicated rather than
    imported (see module docstring above).
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

    return templates.TemplateResponse(request=request, name="aide.html", context={})


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    findings, note = qualified_findings()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "findings": findings,
            "note": note,
            "status": request.query_params.get("status"),
        },
    )


@app.post("/finding/{subject}/start")
def start(subject: str):
    """
    Computes `reason`/`explain`/`recommend` together, over the real,
    freshly re-collected finding for `subject` — exactly the same
    three calls `aistack.cli.ai_reason.main()` makes in its own loop
    body — records them as one combined entry (J7's own decision #2,
    `claude/PLAN-J7-AI-REASONING-HISTORY-2026-09-18.md`) immediately,
    before showing a single step: traceability does not wait on
    whether the owner clicks all the way through the wizard.
    """

    findings, _ = qualified_findings()
    finding = next((f for f in findings if f.subject == subject), None)

    if finding is None:
        status = f"Panne introuvable ou déjà résolue : {subject}"
        return RedirectResponse(f"/?status={quote(status)}", status_code=303)

    ai_runtime_definition = load_ai_runtime_yaml(AI_RUNTIME_PATH)

    # Built even when `model` is empty — same note
    # `aistack.cli.ai_reason.main()` already carries for the same
    # construction.
    engine = OllamaEngine(
        host=ai_runtime_definition.host,
        port=ai_runtime_definition.port,
        model=ai_runtime_definition.model or "",
    )

    answers: tuple[AIRuntimeAnswer, AIRuntimeAnswer, AIRuntimeAnswer] = (
        reason(finding, engine, ai_runtime_definition.model),
        explain(finding, engine, ai_runtime_definition.model),
        recommend(finding, engine, ai_runtime_definition.model),
    )

    record_ai_reasoning(finding, answers)

    _SESSIONS[subject] = {
        "finding": finding,
        "answers": {
            "reason": answers[0],
            "explain": answers[1],
            "recommend": answers[2],
        },
    }

    return RedirectResponse(f"/finding/{quote(subject)}/step/1", status_code=303)


@app.get("/finding/{subject}/step/{step}", response_class=HTMLResponse)
def step(request: Request, subject: str, step: int):
    session = _SESSIONS.get(subject)

    if session is None or step < 1 or step > _STEP_COUNT:
        status = f"Session expirée pour {subject} — relance depuis la liste."
        return RedirectResponse(f"/?status={quote(status)}", status_code=303)

    operation = _OPERATION_BY_STEP.get(step)
    answers = session["answers"]
    assert isinstance(answers, dict)
    answer = answers[operation] if operation else None

    return templates.TemplateResponse(
        request=request,
        name="step.html",
        context={
            "subject": subject,
            "step": step,
            "total_steps": _STEP_COUNT,
            "finding": session["finding"],
            "answer": answer,
        },
    )


@app.post("/finding/{subject}/apply")
def apply(subject: str):
    """
    Applies the one, single-click-safe fix this assistant knows how
    to make: declaring `subject` a background container in the
    governed resource-priority definition — exactly the write
    `priority_ui/app.py`'s own `/save` route already performs in
    production (`save_resource_priority_yaml`), scoped here to one
    container instead of a full-form rewrite.

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
    """

    definition, note = resource_priority_definition(RESOURCE_PRIORITY_PATH)

    if definition is None:
        _SESSIONS.setdefault(subject, {})["applied"] = {
            "outcome": "error",
            "message": note,
        }
        return RedirectResponse(
            f"/finding/{quote(subject)}/applied", status_code=303
        )

    already_priority = any(
        app_def.container == subject for app_def in definition.priority
    )
    already_background = any(
        container.name == subject
        for container in definition.background.containers
    )

    if already_priority:
        _SESSIONS.setdefault(subject, {})["applied"] = {
            "outcome": "refused",
            "message": (
                f"{subject} est déjà classé « priority » dans "
                f"resource_priority.yml — cet assistant ne sait "
                f"appliquer que le classement « background » (utilise "
                f"priority_ui, http://GIGABYTE:8182, pour changer un "
                f"classement priority)."
            ),
        }
        return RedirectResponse(
            f"/finding/{quote(subject)}/applied", status_code=303
        )

    if already_background:
        action_message = (
            f"{subject} était déjà classé « background » dans "
            f"resource_priority.yml — rien à écrire."
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
        action_message = (
            f"{subject} ajouté à background.containers dans "
            f"resource_priority.yml (ralenti partagé : "
            f"{updated.background.default_throttled_cpus} CPU dès que le "
            f"moniteur resource-priority tourne)."
        )

    findings_after, _ = qualified_findings()
    still_present = any(f.subject == subject for f in findings_after)

    _SESSIONS.setdefault(subject, {})["applied"] = {
        "outcome": "unresolved" if still_present else "resolved",
        "message": action_message,
        "still_present": still_present,
    }

    return RedirectResponse(f"/finding/{quote(subject)}/applied", status_code=303)


@app.get("/finding/{subject}/applied", response_class=HTMLResponse)
def applied(request: Request, subject: str):
    session = _SESSIONS.get(subject) or {}
    result = session.get("applied")

    if result is None:
        status = f"Aucune application en cours pour {subject} — relance depuis la liste."
        return RedirectResponse(f"/?status={quote(status)}", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="applied.html",
        context={"subject": subject, "result": result},
    )
