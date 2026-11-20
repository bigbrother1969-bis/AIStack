"""*Sécurité*: the security report, its graphs, the maintenance window, and a
fiche per finding with the local AI's opinion (ADR-0028 slice T4b).

LAN only. Read-only on the hosts: the one thing a person can do here is
declare a maintenance window, through the `security.window` Task; the AI
is asked on a click, goes to the local engine only (never Gemini), and its
answer is shown as a suggestion, never run. `run_window` and `ask_local`
are injected so tests can replace them.

Sessions of the AI sit in memory, one per finding key. The three answers
are recorded together (`ai-reasoning/`) when the last arrives.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.ai_runtime.reasoning_history import record_ai_reasoning
from aistack.config import PACKAGE_ROOT, configured
from aistack.contracts.runtime_finding import MatchedLine, RuntimeFinding
from aistack.contracts.runtime_observation import LogEntry
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.security import screen, series, window
from aistack.security.yaml import load_security_yaml
from aistack.troubleshooting.guide import OPERATIONS, describe_unreachable, run_diagnosis
from aistack.vigil.notify import read_state
from aistack.web.authentication import ADMIN_ACTION, SIGNED_IN_ONLY, current_session
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/security"
DEFINITION = configured(PACKAGE_ROOT / "security" / "definitions" / "security.yml")
DURATIONS = ("30m", "1h", "2h", "4h")

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def _render(request: Request, name: str, context: dict[str, object]) -> Response:
    language = _language(request)
    response = templates.TemplateResponse(
        request=request,
        name=f"security/{name}",
        context={**context, "base": PREFIX, **language.context()},
    )
    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)
    return response


def _sessions(request: Request) -> dict[str, dict[str, Any]]:
    sessions: dict[str, dict[str, Any]] = request.app.state.security_sessions
    return sessions


def _watch_since(generated_dir: Path) -> dict[str, str]:
    return dict(read_state(generated_dir).watch_since)


def _local(value: datetime, zone_name: str) -> str:
    return value.astimezone(window.zone(zone_name)).strftime("%H:%M")


def _age(t: Any, since: datetime | None, now: datetime) -> str:
    if since is None or now - since < timedelta(hours=1):
        return t("notify.age.recent")
    hours = int((now - since).total_seconds() // 3600)
    return t("notify.age.hours", n=hours) if hours < 48 else t("notify.age.days", n=hours // 24)


def run_window(generated_dir: Path, action: str, duration: str = "") -> dict[str, Any]:
    """Execute the `security.window` Task through the Runtime, as the command line does."""

    from aistack.kernel.runtime import KernelRuntime, Request as RuntimeRequest
    from aistack.kernel.tracing import FileTraceRepository
    from aistack.tasks.security_window import SecurityWindowTask

    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository(output_path=generated_dir / "execution-trace.json"))
    request = RuntimeRequest(
        request_id=str(uuid.uuid4()),
        task_id=SecurityWindowTask.task_id,
        payload={"generated_dir": str(generated_dir), "action": action, "duration": duration},
    )
    data: dict[str, Any] = dict(runtime.execute(request).observation.data)
    return data


def local_model() -> str:
    """The model of the local engine; empty when none is declared."""

    from aistack.ai_runtime.yaml import load_ai_runtime_yaml
    from aistack.troubleshooting.guide import AI_RUNTIME

    return load_ai_runtime_yaml(AI_RUNTIME).model or ""


def _graphs(request: Request, series_lines: list[dict[str, Any]], start: datetime, end: datetime, zone_name: str) -> list[dict[str, Any]]:
    t = _language(request).t
    zone = window.zone(zone_name)
    out = []
    for graph in screen.GRAPHS:
        labels = {line.label: t(f"security.graphs.{graph.title}.{line.label}") for line in graph.lines}
        labels["none"] = t("security.graphs.none")
        picture = screen.svg(
            series_lines, graph, start, end, labels, t(f"security.graphs.{graph.title}.description"), zone
        )
        legend = [{"label": labels[line.label], "colour": line.colour} for line in graph.lines]
        out.append({"title": t(f"security.graphs.{graph.title}.title"), "svg": picture, "legend": legend})
    return out


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    t = _language(request).t
    generated = request.app.state.generated_dir
    now = datetime.now(timezone.utc)
    definition = load_security_yaml(DEFINITION)
    report = series.read_report(generated)
    opened = window.current(generated, now)
    since = _watch_since(generated)
    counts = {severity: sum(1 for item in screen.findings_of(report) if item.get("severity") == severity) for severity in ("watch", "fix", "urgent")}

    chosen = request.query_params.get("range", screen.DEFAULT_RANGE)
    chosen = chosen if chosen in screen.RANGES else screen.DEFAULT_RANGE
    start = now - screen.RANGES[chosen]
    lines = series.read(generated, start - timedelta(hours=2))
    collected = screen.instant(report.get("collected_at")) if report else None

    def shown(group: str) -> list[dict[str, Any]]:
        return [
            {"row": row, "age": _age(t, row.since, now) if row.since else ""}
            for row in screen.rows(report, opened is not None, since, only=group)
        ]

    return _render(
        request,
        "index.html",
        {
            "status": request.query_params.get("status"),
            "has_report": report is not None,
            "collected_at": _local(collected, definition.digest_timezone) if collected else "",
            "minutes_old": int((now - collected).total_seconds() // 60) if collected else 0,
            "stale": collected is None or now - collected > timedelta(hours=3),
            "counts": counts,
            "information": screen.information_count(report),
            "groups": [
                {"title": t(f"security.group.{name}"), "intro": t(f"security.group.{name}_intro"), "rows": shown(name)}
                for name in (screen.ATTACKS, screen.VULNERABILITIES)
            ],
            "sources": [{"title": item.get("title", item["key"]), "severity": item.get("severity")} for item in screen.source_problems(report)],
            "window_open": opened is not None,
            "window_until": _local(opened.until, definition.digest_timezone) if opened else "",
            "window_minutes": int(opened.remaining(now).total_seconds() // 60) if opened else 0,
            "window_hours": definition.window_max_hours,
            "durations": [d for d in DURATIONS if window.parse_duration(d) <= timedelta(hours=definition.window_max_hours)],
            "ranges": [{"name": name, "label": t(f"security.graphs.range.{name}")} for name in screen.RANGES],
            "range": chosen,
            "graphs": _graphs(request, lines, start, now, definition.digest_timezone),
            "level_word": lambda level: t(f"security.level.{level}"),
        },
    )


def _back(status: str) -> RedirectResponse:
    return RedirectResponse(f"{PREFIX}/?status={quote(status)}", status_code=303)


@router.post("/window", include_in_schema=False, dependencies=[ADMIN_ACTION])
def declare_window(request: Request, action: str = Form(""), duration: str = Form("")) -> RedirectResponse:
    t = _language(request).t
    definition = load_security_yaml(DEFINITION)
    data = request.app.state.security_window(request.app.state.generated_dir, "end" if action == "end" else "open", duration)

    if not data.get("ok", False):
        return _back(t("security.window.refused", error=str(data.get("error", ""))))
    if action == "end":
        return _back(t("security.window.closed"))
    until = screen.instant(data.get("until"))
    return _back(t("security.window.opened", until=_local(until, definition.digest_timezone) if until else ""))


def _row(request: Request, key: str) -> screen.Row | None:
    generated = request.app.state.generated_dir
    report = series.read_report(generated)
    for item in screen.findings_of(report):
        if item["key"] == key:
            return screen.Row(
                key=key,
                severity=str(item.get("severity")),
                title=str(item.get("title", key)),
                evidence=tuple(str(line) for line in item.get("evidence") or []),
                unknown=str(item.get("unknown") or ""),
                held=False,
                since=None,
                kind=screen.kind_of(key),
            )
    return None


def _runtime_finding(row: screen.Row, t: Any) -> RuntimeFinding:
    """The finding as the engine's prompts know it: the fixed texts say what it means and what to do;
    the evidence is cleaned (`screen.clean_line`) before it becomes a line."""

    lines = [screen.clean_line(line) for line in row.evidence[: screen.EVIDENCE_LINES]] or [screen.clean_line(row.title)]
    return RuntimeFinding(
        subject=f"security:{row.key}",
        signature=f"ADR-0028/{row.kind}",
        interpretation=t(f"security.guide.{row.kind}.meaning"),
        remediation=t(f"security.guide.{row.kind}.action"),
        confidence=row.severity,
        grounding="security assessment",
        evidence=tuple(MatchedLine(LogEntry(offset=index, text=line)) for index, line in enumerate(lines)),
    )


def _href(key: str) -> str:
    return f"{PREFIX}/finding/{quote(key)}"


@router.get("/finding/{key:path}", response_class=HTMLResponse, include_in_schema=False)
def finding(request: Request, key: str) -> Response:
    language = _language(request)
    t = language.t
    row = _row(request, key)

    if row is None:
        return _back(t("security.finding.missing"))

    session = _sessions(request).get(key)
    answers = session["answers"] if session else {}
    person = current_session(request)
    if person is not None:
        for operation in answers:
            request.app.state.ai_jobs.seen(person.subject, f"{_href(key)}#ai-{operation}")

    opinions = []
    for operation in OPERATIONS:
        answer = answers.get(operation)
        unreachable = ""
        if answer is not None and not answer.reachable:
            message_key, parameters = describe_unreachable(answer.unreachable_reason)
            unreachable = t(message_key, **parameters)
        opinions.append({"operation": operation, "answer": answer, "unreachable": unreachable})

    model = request.app.state.local_model()

    return _render(
        request,
        "finding.html",
        {
            "key": key,
            "row": row,
            "level": row.severity,
            "level_word": t(f"security.level.{row.severity}"),
            "guide": {part: t(f"security.guide.{row.kind}.{part}") for part in ("meaning", "check", "action")},
            "labels": {operation: t(f"security.finding.ai.{operation}") for operation in OPERATIONS},
            "model": model,
            "asked": bool(session and session.get("asked")),
            "opinions": opinions,
            "pending": bool(session and session.get("asked")) and len(answers) < len(OPERATIONS),
            "evidence": [screen.clean_line(line) for line in row.evidence],
        },
    )


@router.post("/finding/{key:path}/ask", include_in_schema=False, dependencies=[ADMIN_ACTION])
def ask(request: Request, key: str) -> RedirectResponse:
    """Ask the local engine (`reason`, `explain`, `recommend`) in the background, once per session."""

    language = _language(request)
    row = _row(request, key)
    target = RedirectResponse(_href(key), status_code=303)

    if row is None:
        return _back(language.t("security.finding.missing"))

    sessions = _sessions(request)
    session = sessions.get(key)
    if session is not None and session.get("asked"):
        return target

    session = {"answers": {}, "asked": True}
    sessions[key] = session
    finding_for_engine = _runtime_finding(row, language.t)
    context = screen.facts_for_engine(row, language.t)
    history = request.app.state.generated_dir / "ai-reasoning"
    ask_local = request.app.state.ask_local_ai
    jobs = request.app.state.ai_jobs
    job_id = f"security:{key}"
    person = current_session(request)
    jobs.start(job_id, person.subject if person else "", row.title, len(OPERATIONS))

    def announce(operation: str) -> None:
        jobs.answered(job_id, f"security.finding.ai.{operation}", f"{_href(key)}#ai-{operation}")

    request.app.state.run_in_background(
        lambda: run_diagnosis(
            finding_for_engine,
            language.lang,
            session["answers"],
            ask_local,
            lambda found, done: record_ai_reasoning(found, done, history),
            announce,
            context,
        )
    )
    return target
