"""
*Assistant de pannes* — a guided, step-by-step diagnosis of one real
finding (`ADR-0012`; the screen `troubleshooting_assistant_ui` served
on port 8185 until 2026-10-03). LAN only: it calls the AI Runtime and
its one fix writes the governed resource-priority definition.

A thin adapter over `aistack.troubleshooting`. Three collaborators
reach the routes through the application, so a test replaces each:
`collect_findings` (the host's findings, fresh), `ask_ai` (Ollama) and
nothing else — the definition and the reasoning history are written
under paths the application was given.

**One in-memory session per finding key, deliberately not persisted**:
the answers are persisted together the moment the last one arrives
(`reports/generated/ai-reasoning/`), so a restart only means a fresh
Ollama round-trip — or, during a diagnosis, losing the answers already
received for it, which were never recorded on their own.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.ai_runtime.reasoning_history import record_ai_reasoning
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.priority.yaml import save_resource_priority_yaml
from aistack.troubleshooting.apply import BackgroundChange, class_as_background
from aistack.troubleshooting.findings import CONSUMPTION_DOMAIN, resource_priority_definition
from aistack.troubleshooting.guide import (
    OPERATION_BY_STEP,
    OPERATIONS,
    STEP_COUNT,
    describe_unreachable,
    run_diagnosis,
)
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/troubleshooting"

router = APIRouter(dependencies=[LAN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def _sessions(request: Request) -> dict[str, dict[str, object]]:
    sessions: dict[str, dict[str, object]] = request.app.state.troubleshooting_sessions

    return sessions


def _render(request: Request, name: str, context: dict[str, object]) -> Response:
    language = _language(request)
    response = templates.TemplateResponse(
        request=request,
        name=f"troubleshooting/{name}",
        context={**context, "base": PREFIX, **language.context()},
    )

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response


def _back_to_list(status: str) -> RedirectResponse:
    return RedirectResponse(f"{PREFIX}/?status={quote(status)}", status_code=303)


@router.get("/aide", response_class=HTMLResponse, include_in_schema=False)
def aide(request: Request) -> Response:
    """
    Hand-written help — opening a terminal, reaching GIGABYTE over SSH,
    pasting a command. Fixed, verified content, never AI-generated per
    finding (the owner's choice, 2026-09-18).
    """

    return _render(request, "aide.html", {})


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    findings, note = request.app.state.collect_findings()

    return _render(
        request,
        "index.html",
        {"findings": findings, "note": note, "status": request.query_params.get("status")},
    )


@router.post("/finding/{key}/start", include_in_schema=False)
def start(request: Request, key: str) -> RedirectResponse:
    """
    Start the diagnosis of the finding routed by `key`, freshly
    re-collected, in the background, and open its first step at once.

    The three answers arrive one by one into the session; the steps
    show each as soon as it exists. A diagnosis already running for
    this key is joined, never started twice — the model works on one
    call at a time on this host.
    """

    language = _language(request)
    sessions = _sessions(request)
    first_step = RedirectResponse(f"{PREFIX}/finding/{quote(key)}/step/1", status_code=303)

    running = sessions.get(key)
    if running is not None and len(running["answers"]) < len(OPERATIONS):  # type: ignore[arg-type]
        return first_step

    findings, _ = request.app.state.collect_findings()
    entry = next((f for f in findings if f.key == key), None)

    if entry is None:
        return _back_to_list(language.t("troubleshooting.status.not_found", subject=key))

    answers: dict[str, object] = {}
    sessions[key] = {
        "finding": entry.finding,
        "domain": entry.domain,
        "applyable": entry.applyable,
        "answers": answers,
    }

    history = request.app.state.generated_dir / "ai-reasoning"
    ask = request.app.state.ask_ai

    request.app.state.run_in_background(
        lambda: run_diagnosis(
            entry.finding,
            language.lang,
            answers,  # type: ignore[arg-type]
            ask,
            lambda finding, done: record_ai_reasoning(finding, done, history),
        )
    )

    return first_step


@router.get("/finding/{key}/step/{step}", response_class=HTMLResponse, include_in_schema=False)
def step(request: Request, key: str, step: int) -> Response:
    session = _sessions(request).get(key)

    if session is None or step < 1 or step > STEP_COUNT:
        return _back_to_list(_language(request).t("troubleshooting.status.expired", subject=key))

    operation = OPERATION_BY_STEP.get(step)
    answers = session["answers"]
    assert isinstance(answers, dict)
    finding = session["finding"]
    assert isinstance(finding, RuntimeFinding)

    answer = answers.get(operation) if operation else None
    unreachable = ""

    if answer is not None and not answer.reachable:
        message_key, parameters = describe_unreachable(answer.unreachable_reason)
        unreachable = _language(request).t(message_key, **parameters)

    return _render(
        request,
        "step.html",
        {
            "key": key,
            "subject": finding.subject,
            "domain": session["domain"],
            "applyable": session["applyable"],
            "step": step,
            "total_steps": STEP_COUNT,
            "finding": finding,
            "answer": answer,
            # An AI step whose answer has not arrived yet: the page
            # says so and refreshes itself.
            "pending": operation is not None and answer is None,
            "unreachable": unreachable,
        },
    )


@router.post("/finding/{key}/apply", include_in_schema=False)
def apply(request: Request, key: str) -> RedirectResponse:
    """
    The one fix, guarded twice: `step.html` hides the button unless the
    finding is a `CONSUMPTION_DOMAIN` one, and this route refuses the
    same way on a direct POST. **Verified, not assumed**: the findings
    are collected again after saving, and the page says whether this
    subject's consumption finding is actually gone.
    """

    t = _language(request).t
    session = _sessions(request).get(key)

    if session is None or not session.get("applyable"):
        return _back_to_list(t("troubleshooting.status.not_applyable", subject=key))

    finding = session["finding"]
    assert isinstance(finding, RuntimeFinding)
    subject = finding.subject
    path = request.app.state.paths.resource_priority
    applied = RedirectResponse(f"{PREFIX}/finding/{quote(key)}/applied", status_code=303)

    definition, note = resource_priority_definition(path)

    if definition is None:
        session["applied"] = {"outcome": "error", "message": note}
        return applied

    decision = class_as_background(definition, subject)

    if decision.change is BackgroundChange.REFUSED_PRIORITY:
        session["applied"] = {
            "outcome": "refused",
            "message": t("troubleshooting.message.already_priority", subject=subject),
        }
        return applied

    if decision.updated is not None:
        save_resource_priority_yaml(decision.updated, path)
        message = t(
            "troubleshooting.message.added",
            subject=subject,
            cpus=decision.updated.background.default_throttled_cpus,
        )
    else:
        message = t("troubleshooting.message.already_background", subject=subject)

    # Matched on the consumption domain as well as the subject: another
    # domain's finding that merely shares this subject is not one this
    # fix was meant to touch.
    findings_after, _ = request.app.state.collect_findings()
    still_present = any(
        entry.domain == CONSUMPTION_DOMAIN and entry.finding.subject == subject
        for entry in findings_after
    )

    session["applied"] = {
        "outcome": "unresolved" if still_present else "resolved",
        "message": message,
        "still_present": still_present,
    }

    return applied


@router.get("/finding/{key}/applied", response_class=HTMLResponse, include_in_schema=False)
def applied(request: Request, key: str) -> Response:
    session = _sessions(request).get(key) or {}
    result = session.get("applied")

    if result is None:
        return _back_to_list(
            _language(request).t("troubleshooting.status.nothing_applied", subject=key)
        )

    finding = session.get("finding")
    subject = finding.subject if isinstance(finding, RuntimeFinding) else key

    return _render(request, "applied.html", {"subject": subject, "result": result})
