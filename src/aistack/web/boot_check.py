"""*Contrôles du démarrage*: how the host started, and whether all has been well since. ADR-0032, slice B3.

Two small things over what `aistack.cli.boot_check` writes (`boot-check.json`):

- the detail screen, LAN only: every control and its result, the incidents
  since the start (a resolved one stays listed until the next start);
- `/boot-state`, the live answer the strip of the health cockpit asks for
  and draws, for a signed-in person only (anyone else gets `{}`), like the
  badges of `/pending`.

Reading only: the checks are run by the vigil and by the command, the
declaration is edited with the others.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from aistack.ai_runtime import call_journal
from aistack.boot_checks.load import load_boot_checks_yaml
from aistack.boot_checks.phrases import say
from aistack.boot_checks.quality import read_quality, unexplained
from aistack.boot_checks.controls import ANOMALIES
from aistack.boot_checks.history import open_since, read_history
from aistack.boot_checks.screen import LEVELS, companions, elapsed, read_indicator, read_indicators, sentence
from aistack.boot_checks.state import Verdict, read_verdict
from aistack.i18n import Translator
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.web.authentication import SIGNED_IN_ONLY, current_session
from aistack.web.exposure import LAN_ONLY, PUBLIC
from aistack.web.templating import templates

PREFIX = "/boot-check"
# How many of the latest changes the page lists.
HISTORY_SHOWN = 40
STATE_PATH = "/boot-state"

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])
state_router = APIRouter(dependencies=[PUBLIC])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


@state_router.get(STATE_PATH, include_in_schema=False)
def state(request: Request) -> JSONResponse:
    if current_session(request) is None:
        return JSONResponse({})

    t = _language(request).t
    pills = []

    for host, shown in read_indicators(request.app.state.generated_dir):
        text, title = sentence(t, shown, host)
        pills.append({"host": host or "", "level": shown.level, "text": text, "title": title, "status": shown.status})

    return JSONResponse({"pills": pills})


def _stamp(value: str | None) -> str:
    return (value or "")[:16].replace("T", " ")


def _explanation_of(verdict: object, result: object) -> str:
    """The engine's words on an anomaly, when they still concern the control as it is now; empty otherwise."""

    for item in getattr(verdict, "explanations", ()):
        if (item.control, item.status, item.summary) == (result.control, result.status, result.summary):  # type: ignore[attr-defined]
            return item.text  # type: ignore[no-any-return]

    return ""


def _basis_of(verdict: object, result: object) -> tuple[str, ...]:
    """What the explanation of an anomaly rests on besides its sentence (O9): the containers whose log lines were read."""

    for item in getattr(verdict, "explanations", ()):
        if (item.control, item.status, item.summary) == (result.control, result.status, result.summary):  # type: ignore[attr-defined]
            return item.basis  # type: ignore[no-any-return]

    return ()


def _choice(t: Translator, verdict: object) -> str:
    """Who chose the extra controls: the engine (and what it said) or the rules; empty when nothing was to choose."""

    if verdict is None or not getattr(verdict, "circumstances", ()) or not getattr(verdict, "chosen_by", ""):
        return ""

    if verdict.chosen_by == "engine":  # type: ignore[attr-defined]
        return t("boot_check.choice.engine", reason=verdict.choice_reason or t("boot_check.choice.no_reason"))  # type: ignore[attr-defined]

    return t("boot_check.choice.rules")


def _section(t: Translator, host: str | None, generated_dir: Path, now: datetime) -> dict[str, object]:
    """One machine's part of the page: its verdict, its controls, its incidents."""

    verdict = read_verdict(generated_dir, host)
    shown = read_indicator(generated_dir, now, host)
    journal = read_history(generated_dir, host)
    rows = [
        {
            "label": t(f"boot_check.control.{result.control}"),
            "status": result.status,
            "status_label": t(f"boot_check.status.{result.status}"),
            "summary": say(t, result.summary),
            "details": tuple(say(t, detail) for detail in result.details),
            "extra": result.control in (verdict.extra if verdict else ()),
            "explanation": _explanation_of(verdict, result),
            "basis": tuple(say(t, line) for line in _basis_of(verdict, result)),
            "since": _stamp(open_since(journal, result.control)) if result.status in ANOMALIES else "",
        }
        for result in (verdict.results if verdict else ())
    ]
    incidents = [
        {
            "label": t(f"boot_check.control.{item.control}"),
            "summary": say(t, item.summary),
            "open": item.resolved_at is None,
            "first": _stamp(item.first_seen),
            "last": _stamp(item.resolved_at),
            "before": None if item.before is None else tuple(say(t, line) for line in item.before),
        }
        for item in (verdict.incidents if verdict else ())
    ]

    history = [
        {
            "at": _stamp(event.at),
            "label": t(f"boot_check.control.{event.control}"),
            "status": event.status,
            "status_label": t(f"boot_check.status.{event.status}"),
            "summary": say(t, event.summary),
            "details": tuple(say(t, detail) for detail in event.details),
        }
        for event in reversed(journal[-HISTORY_SHOWN:])
    ]

    return {
        "host": host,
        "history": history,
        "verdict": verdict,
        "shown": shown,
        "level": LEVELS.get(shown.status, "not-instrumented"),
        "elapsed": elapsed(t, shown.elapsed_seconds) if shown.elapsed_seconds is not None else "",
        "rows": rows,
        "circumstances": [t(f"boot_check.circumstance.{item}") for item in (verdict.circumstances if verdict else ())],
        "choice": _choice(t, verdict),
        "incidents": incidents,
        "has_skipped": any(row["status"] == "skipped" for row in rows),
        "booted_at": _stamp(verdict.booted_at) if verdict else "",
        "checked_at": _stamp(verdict.checked_at) if verdict else "",
    }


def _quality(t: Translator, generated_dir: Path, verdict: Verdict | None, now: datetime) -> list[str]:
    """How AIStack itself is doing (O10), in sentences: the engine's calls, the anomalies left without words, the last pass."""

    from aistack.tasks.boot_check import DEFAULT_DEFINITION

    try:
        definition = load_boot_checks_yaml(DEFAULT_DEFINITION)
        days, minimum = definition.quality_days, definition.quality_min_calls
    except Exception:  # an unreadable declaration is not a reason to hide the page
        days, minimum = 7, 5

    seen = read_quality(call_journal.read(generated_dir / "ai-calls", 5000), now, days, minimum)
    lines = []

    if seen.enough:
        lines.append(t("boot_check.quality.engine", answered=seen.answered, calls=seen.calls, days=days, median=seen.median, slowest=seen.slowest))
    else:
        lines.append(t("boot_check.quality.too_few", calls=seen.calls, days=days, minimum=minimum))

    if verdict is not None and verdict.anomalies:
        left = unexplained(verdict.explanations)
        lines.append(t("boot_check.quality.unexplained", n=left) if left else t("boot_check.quality.explained"))

    took = verdict.took if verdict is not None else None
    lines.append(t("boot_check.quality.took", seconds=took) if took is not None else t("boot_check.quality.took_unknown"))

    return lines


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    language = _language(request)
    now = datetime.now(timezone.utc)
    generated_dir = request.app.state.generated_dir
    sections = [_section(language.t, host, generated_dir, now) for host in (None, *companions(generated_dir))]
    quality = _quality(language.t, generated_dir, read_verdict(generated_dir), now)
    context: dict[str, object] = {"base": PREFIX, "sections": sections, "quality": quality, **language.context()}
    response = templates.TemplateResponse(request=request, name="boot_check/index.html", context=context)

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response


# Injected before `</body>` for a signed-in person, after the badges' script:
# on a page with the strip's indicator it asks `/boot-state` and says how the
# start is going, elsewhere it does nothing. The console page itself stays
# script-free, and keeps its static label when nobody is signed in.
SNIPPET = """<script>
(function () {
  var mark = document.getElementById("boot-indicator");
  if (!mark || !window.fetch) { return; }
  function draw(node, found) {
    node.textContent = found.text;
    node.className = "domain-badge badge-" + found.level;
    node.title = found.title;
  }
  fetch("/boot-state" + window.location.search, { credentials: "same-origin", headers: { "Accept": "application/json" } })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .then(function (found) {
      var pills = found && found.pills;
      if (!pills || !pills.length) { return; }
      draw(mark, pills[0]);
      var last = mark.parentNode;
      for (var i = 1; i < pills.length; i++) {
        var more = document.createElement("a");
        more.href = "/boot-check/#" + encodeURIComponent(pills[i].host);
        draw(more, pills[i]);
        mark.parentNode.appendChild(more);
      }
    })
    .catch(function () {});
})();
</script>
"""
