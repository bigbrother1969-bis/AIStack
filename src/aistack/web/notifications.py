"""
`/notifications` — the AI answers ready for the signed-in person and
not yet opened (`aistack.web.ai_jobs`), for the notice every page shows
(owner, 2026-10-09). LAN only, like every screen that asks the AI.

    {"running": 1, "ready": [{"id": "...", "text": "...", "href": "..."}]}

`running` tells the page how soon to ask again: every 10 s while an
answer is still coming, every 30 s otherwise.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import page_language
from aistack.web.ai_jobs import AIJobs
from aistack.web.authentication import current_session
from aistack.web.exposure import LAN_ONLY

PATH = "/notifications"
POLL_SECONDS = 10
# Nothing coming: asked again now and then, so a tab opened before a
# diagnosis started still hears of its answers.
IDLE_SECONDS = 30

router = APIRouter(dependencies=[LAN_ONLY])


def jobs_of(request: Request) -> AIJobs:
    jobs: AIJobs = request.app.state.ai_jobs
    return jobs


def owner_of(request: Request) -> str:
    session = current_session(request)
    return session.subject if session is not None else ""


@router.get(PATH, include_in_schema=False)
def notifications(request: Request) -> JSONResponse:
    owner = owner_of(request)
    if not owner:
        return JSONResponse({"running": 0, "ready": []})
    t = page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    ).t
    running, ready = jobs_of(request).for_owner(owner)
    return JSONResponse({
        "running": running,
        "ready": [
            {
                "id": f"{job.id}#{item.number}",
                "text": t("common.notice.ready", label=t(item.label), subject=job.subject),
                "href": item.href,
            }
            for job, item in ready
        ],
    })


# The notice every page carries on the local-network listener, for a
# signed-in person: a corner of the page, and a few lines of script that
# ask `/notifications` — every 10 s while an answer is coming, every
# 30 s otherwise.
SNIPPET = """<div id="aistack-notices" aria-live="polite"></div>
<style>
#aistack-notices { position: fixed; right: 1rem; bottom: 1rem; z-index: 1000; display: flex; flex-direction: column; gap: .5rem; max-width: 26rem; }
.aistack-notice { display: flex; align-items: flex-start; gap: .5rem; background: #16335c; color: #fff; border-radius: 8px; padding: .7rem .9rem; box-shadow: 0 4px 14px rgba(0,0,0,.25); font: 500 .9rem/1.35 system-ui, sans-serif; }
.aistack-notice a { color: #fff; text-decoration: underline; flex: 1; }
.aistack-notice button { background: none; border: 0; color: #fff; font-size: 1.1rem; line-height: 1; cursor: pointer; padding: 0 .1rem; }
</style>
<script>
(function () {
  var box = document.getElementById("aistack-notices");
  if (!box || !window.fetch) { return; }
  var shown = {}, timer = null, KEY = "aistack-notices-dismissed";
  function dismissed() { try { return JSON.parse(sessionStorage.getItem(KEY) || "[]"); } catch (e) { return []; } }
  function dismiss(id) { try { var d = dismissed(); d.push(id); sessionStorage.setItem(KEY, JSON.stringify(d)); } catch (e) {} }
  function show(n) {
    if (shown[n.id] || dismissed().indexOf(n.id) >= 0) { return; }
    shown[n.id] = true;
    var wrap = document.createElement("div"); wrap.className = "aistack-notice"; wrap.setAttribute("role", "status");
    var link = document.createElement("a"); link.href = n.href; link.textContent = n.text; link.title = __OPEN__;
    var close = document.createElement("button"); close.type = "button"; close.textContent = "\\u00d7";
    close.title = __CLOSE__; close.setAttribute("aria-label", __CLOSE__);
    close.onclick = function () { dismiss(n.id); wrap.remove(); };
    wrap.appendChild(link); wrap.appendChild(close); box.appendChild(wrap);
  }
  function poll() {
    fetch("__PATH__", { credentials: "same-origin", headers: { "Accept": "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) { return; }
        d.ready.forEach(show);
        clearTimeout(timer);
        timer = setTimeout(poll, d.running > 0 ? __POLL__ : __IDLE__);
      })
      .catch(function () {});
  }
  poll();
})();
</script>
"""


def snippet(t: Callable[..., str]) -> str:
    """The notice, its two words in the reader's language — as JSON
    strings, so no text can end the script."""

    return (
        SNIPPET.replace("__PATH__", PATH)
        .replace("__POLL__", str(POLL_SECONDS * 1000))
        .replace("__IDLE__", str(IDLE_SECONDS * 1000))
        .replace("__OPEN__", json.dumps(t("common.notice.open")).replace("</", "<\\/"))
        .replace("__CLOSE__", json.dumps(t("common.notice.close")).replace("</", "<\\/"))
    )
