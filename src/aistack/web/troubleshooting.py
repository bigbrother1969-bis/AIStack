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

import time
from datetime import date, datetime, timezone
from datetime import time as dt_time
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.ai_runtime.reasoning_history import record_ai_reasoning
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.findings import (
    finding_confidence,
    finding_interpretation,
    finding_remediation,
)
from aistack.i18n.web import PageLanguage, page_language
from aistack.priority.yaml import save_resource_priority_yaml
from aistack.troubleshooting.apply import BackgroundChange, class_as_background
from aistack.troubleshooting.findings import CONSUMPTION_DOMAIN, resource_priority_definition
from aistack.contracts.pra_test_reading import FAILED, SUCCESS
from aistack.pra.scheduled import ScheduledTest
from aistack.pra.scheduled import record as record_pra
from aistack.troubleshooting.facts import PRA_TESTS, Declarations, guidance
from aistack.troubleshooting.guide import (
    AI_STEP,
    OPERATIONS,
    STEP_COUNT,
    describe_unreachable,
    run_diagnosis,
)
from aistack.web.authentication import ADMIN_ACTION, SIGNED_IN_ONLY, current_session
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/troubleshooting"

# How long a CPU finding the list showed can still be started once a
# fresh reading no longer sees it (UAT, 2026-10-09: aistack-docker-digest
# at 18.9 % on the list, under 5 % the second the owner clicked).
LISTED_FOR_SECONDS = 15 * 60

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])


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
        context={
            **context,
            "base": PREFIX,
            # A finding's sentences in the reader's language (ADR-0010
            # § 4, revised 2026-10-03).
            "interpretation_of": lambda finding: finding_interpretation(finding, language.t),
            "remediation_of": lambda finding: finding_remediation(finding, language.t),
            "confidence_of": lambda finding: finding_confidence(finding, language.t),
            **language.context(),
        },
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

    return _render(request, "aide.html", {"host": request.app.state.instance_config.lan_hostname})


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    findings, note = request.app.state.collect_findings()
    now = time.monotonic()
    request.app.state.troubleshooting_listed = {
        entry.key: (entry, now) for entry in findings if entry.domain == CONSUMPTION_DOMAIN
    }

    return _render(
        request,
        "index.html",
        {"findings": findings, "note": note, "status": request.query_params.get("status")},
    )


@router.post("/finding/{key:path}/start", include_in_schema=False, dependencies=[ADMIN_ACTION])
def start(request: Request, key: str) -> RedirectResponse:
    """
    Open the finding routed by `key`, freshly re-collected: the finding,
    the facts AIStack has of it and what to do are shown at once, with
    no AI (2026-10-09). The AI's opinion is asked on step 4 only, on a
    click (`ask`). A session already open for this key is kept, with
    whatever the AI already answered.
    """

    language = _language(request)
    sessions = _sessions(request)
    first_step = RedirectResponse(f"{PREFIX}/finding/{quote(key)}/step/1", status_code=303)

    findings, _ = request.app.state.collect_findings()
    entry = next((f for f in findings if f.key == key), None)

    if entry is None:
        # A CPU reading is an instant: the one the list showed is the
        # one the owner asks about, while it is recent. A cockpit
        # finding gone from a fresh collection is resolved.
        listed = request.app.state.troubleshooting_listed.get(key)
        if listed is not None and time.monotonic() - listed[1] <= LISTED_FOR_SECONDS:
            entry = listed[0]

    if entry is None:
        return _back_to_list(language.t("troubleshooting.status.not_found", subject=key))

    running = sessions.get(key)
    if running is not None and running.get("asked"):
        return first_step

    sessions[key] = {
        "finding": entry.finding,
        "domain": entry.domain,
        "applyable": entry.applyable,
        "answers": {},
        "asked": False,
    }
    return first_step


@router.post("/finding/{key:path}/ask", include_in_schema=False, dependencies=[ADMIN_ACTION])
def ask(request: Request, key: str) -> RedirectResponse:
    """
    Ask the AI's opinion — `reason`, `explain`, `recommend` — in the
    background; each answer appears on step 4 as it arrives and is
    announced on whatever page the owner is. Asked once per session:
    the model works on one call at a time on this host.
    """

    language = _language(request)
    session = _sessions(request).get(key)
    ai_step = RedirectResponse(step_href(key, AI_STEP), status_code=303)

    if session is None:
        return _back_to_list(language.t("troubleshooting.status.expired", subject=key))
    if session.get("asked"):
        return ai_step

    session["asked"] = True
    finding = session["finding"]
    assert isinstance(finding, RuntimeFinding)
    answers = session["answers"]

    history = request.app.state.generated_dir / "ai-reasoning"
    ai = request.app.state.ask_ai
    # The facts of step 2 go with the question (the owner, 2026-10-09).
    context = "\n".join(f"- {fact.label}: {fact.value}" for fact in _guide(request, session).facts)

    jobs = request.app.state.ai_jobs
    job_id = f"troubleshooting:{key}"
    person = current_session(request)
    jobs.start(job_id, person.subject if person else "", finding.subject, len(OPERATIONS))

    def announce(operation: str) -> None:
        jobs.answered(job_id, f"troubleshooting.step.{operation}", answer_href(key, operation))

    request.app.state.run_in_background(
        lambda: run_diagnosis(
            finding,
            language.lang,
            answers,  # type: ignore[arg-type]
            ai,
            lambda found, done: record_ai_reasoning(found, done, history),
            announce,
            context,
        )
    )

    return ai_step


def _guide(request: Request, session: dict[str, object]) -> Any:
    finding = session["finding"]
    assert isinstance(finding, RuntimeFinding)
    paths = request.app.state.paths
    t = _language(request).t
    return guidance(
        str(session["domain"]),
        finding,
        t,
        Declarations(paths.backup_strategy, paths.pra_tests, paths.resource_priority),
        finding_remediation(finding, t),
    )


def answer_href(key: str, operation: str) -> str:
    return f"{step_href(key, AI_STEP)}#ai-{operation}"


def step_href(key: str, step: int) -> str:
    return f"{PREFIX}/finding/{quote(key)}/step/{step}"


@router.get("/finding/{key:path}/step/{step}", response_class=HTMLResponse, include_in_schema=False)
def step(request: Request, key: str, step: int) -> Response:
    session = _sessions(request).get(key)

    if session is None or step < 1 or step > STEP_COUNT:
        return _back_to_list(_language(request).t("troubleshooting.status.expired", subject=key))

    answers = session["answers"]
    assert isinstance(answers, dict)
    finding = session["finding"]
    assert isinstance(finding, RuntimeFinding)
    language = _language(request)

    if step == AI_STEP:
        person = current_session(request)
        if person is not None:
            for operation in answers:
                request.app.state.ai_jobs.seen(person.subject, answer_href(key, operation))

    opinions = []
    for operation in OPERATIONS:
        answer = answers.get(operation)
        unreachable = ""
        if answer is not None and not answer.reachable:
            message_key, parameters = describe_unreachable(answer.unreachable_reason)
            unreachable = language.t(message_key, **parameters)
        opinions.append({"operation": operation, "answer": answer, "unreachable": unreachable})

    domain = str(session["domain"])
    guide = _guide(request, session)
    destination = request.app.state.ai_destination() if step == AI_STEP else ("", "")

    return _render(
        request,
        "step.html",
        {
            "key": key,
            "subject": finding.subject,
            "domain": domain,
            "applyable": session["applyable"],
            "step": step,
            "total_steps": STEP_COUNT,
            "ai_step": AI_STEP,
            "finding": finding,
            "guide": guide,
            "today": date.today().isoformat(),
            "destination": destination[0],
            "destination_model": destination[1],
            "asked": bool(session.get("asked")),
            "opinions": opinions,
            # The AI asked and an answer not there yet: the page says
            # so and refreshes itself.
            "pending": step == AI_STEP and bool(session.get("asked")) and len(answers) < len(OPERATIONS),
        },
    )


@router.post("/finding/{key:path}/apply", include_in_schema=False, dependencies=[ADMIN_ACTION])
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


@router.post("/finding/{key:path}/record", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def record_test(request: Request, key: str) -> RedirectResponse:
    """
    Record the restore test the owner made, from the assistant (UAT,
    2026-10-09: "pas de bouton Appliquer"). AIStack cannot run a test
    that boots the host on rescue media; it records the owner's result
    where the scheduled tests go (`pra/scheduled.jsonl`, `ADR-0018`
    § 8), never in the owner's `pra_tests.yml`, and collects the
    findings again to say whether this one is gone.
    """

    t = _language(request).t
    session = _sessions(request).get(key)
    if session is None or session.get("domain") != PRA_TESTS:
        return _back_to_list(t("troubleshooting.status.not_applyable", subject=key))
    finding = session["finding"]
    assert isinstance(finding, RuntimeFinding)

    form = await request.form()
    status = SUCCESS if form.get("status") == "success" else FAILED
    try:
        day = date.fromisoformat(str(form.get("date") or ""))
    except ValueError:
        day = date.today()
    minutes_text = str(form.get("rto_minutes") or "").strip()
    minutes = int(minutes_text) if minutes_text.isdigit() else None
    method = str(form.get("method") or "").strip()[:200]
    person = current_session(request)
    who = person.subject if person else ""
    now = datetime.now(timezone.utc)
    at = now if day == now.date() else datetime.combine(day, dt_time(12), tzinfo=timezone.utc)

    record_pra(
        request.app.state.generated_dir,
        ScheduledTest(
            service=finding.subject,
            at=at,
            status=status,
            run_id=" — ".join(part for part in ("manual", method, who) if part),
            rto_minutes=minutes if status == SUCCESS else None,
            failure=method if status == FAILED else "",
        ),
    )

    findings_after, _ = request.app.state.collect_findings()
    still_present = any(
        entry.domain == PRA_TESTS and entry.finding.subject == finding.subject for entry in findings_after
    )
    session["applied"] = {
        "outcome": "unresolved" if still_present else "resolved",
        "message": t(
            "troubleshooting.record.done",
            subject=finding.subject,
            status=t(f"troubleshooting.record.{'success' if status == SUCCESS else 'failed'}"),
            date=day.isoformat(),
        ),
        "file": "pra/scheduled.jsonl",
    }
    return RedirectResponse(f"{PREFIX}/finding/{quote(key)}/applied", status_code=303)


@router.get("/finding/{key:path}/applied", response_class=HTMLResponse, include_in_schema=False)
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
