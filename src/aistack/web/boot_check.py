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

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from aistack.boot_checks.screen import LEVELS, elapsed, read_indicator, sentence
from aistack.boot_checks.state import read_verdict
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.web.authentication import SIGNED_IN_ONLY, current_session
from aistack.web.exposure import LAN_ONLY, PUBLIC
from aistack.web.templating import templates

PREFIX = "/boot-check"
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
    shown = read_indicator(request.app.state.generated_dir)
    text, title = sentence(t, shown)

    return JSONResponse({"level": shown.level, "text": text, "title": title, "status": shown.status})


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    language = _language(request)
    t = language.t
    now = datetime.now(timezone.utc)
    verdict = read_verdict(request.app.state.generated_dir)
    shown = read_indicator(request.app.state.generated_dir, now)
    rows = [
        {
            "label": t(f"boot_check.control.{result.control}"),
            "status": result.status,
            "status_label": t(f"boot_check.status.{result.status}"),
            "summary": result.summary,
            "details": result.details,
        }
        for result in (verdict.results if verdict else ())
    ]
    incidents = [
        {
            "label": t(f"boot_check.control.{item.control}"),
            "summary": item.summary,
            "open": item.resolved_at is None,
            "first": item.first_seen[:16].replace("T", " "),
            "last": (item.resolved_at or "")[:16].replace("T", " "),
        }
        for item in (verdict.incidents if verdict else ())
    ]
    context: dict[str, object] = {
        "base": PREFIX,
        "verdict": verdict,
        "shown": shown,
        "level": LEVELS.get(shown.status, "not-instrumented"),
        "elapsed": elapsed(t, shown.elapsed_seconds) if shown.elapsed_seconds is not None else "",
        "rows": rows,
        "incidents": incidents,
        "has_skipped": any(row["status"] == "skipped" for row in rows),
        "booted_at": (verdict.booted_at or "")[:16].replace("T", " ") if verdict else "",
        "checked_at": verdict.checked_at[:16].replace("T", " ") if verdict else "",
        **language.context(),
    }
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
  fetch("/boot-state" + window.location.search, { credentials: "same-origin", headers: { "Accept": "application/json" } })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .then(function (found) {
      if (!found || !found.text) { return; }
      mark.textContent = found.text;
      mark.className = "domain-badge badge-" + found.level;
      mark.title = found.title;
    })
    .catch(function () {});
})();
</script>
"""
