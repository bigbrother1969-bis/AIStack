"""`/pending`: how many actions wait behind each console card, for the badges.

Signed-in sessions only; anyone else gets `{}`.

    {"/dock/": {"count": 1, "text": "1 mise à jour à valider"}, ...}

Counted live from what the screens read: dock proposals awaiting
validation, the findings of the vigil's last pass (`health-state.json`),
and Time Machine Explications proposed but not validated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import page_language
from aistack.web.authentication import current_session
from aistack.web.exposure import PUBLIC

PATH = "/pending"

router = APIRouter(dependencies=[PUBLIC])


def counts(generated_dir: Path) -> dict[str, int]:
    """Card path → how many things wait there; a source that cannot be read counts nothing."""

    found: dict[str, int] = {}

    try:
        from aistack.dock.proposals import PROPOSED, all_proposals

        found["/dock/"] = sum(1 for proposal in all_proposals(generated_dir) if proposal.status == PROPOSED)
    except (OSError, ValueError):
        pass

    from aistack.vigil import snapshot

    taken = snapshot.read(generated_dir)
    if taken is not None:
        found["/troubleshooting/"] = len(taken.findings)

    try:
        from aistack.explications.human import PROPOSED as EXPLICATION_PROPOSED
        from aistack.timemachine.screen import explication_list

        listing: dict[str, Any] = explication_list(generated_dir, EXPLICATION_PROPOSED)
        found["/timemachine/"] = len(listing.get("rows") or [])
    except (OSError, ValueError, KeyError):
        pass

    return {path: count for path, count in found.items() if count > 0}


TEXTS = {
    "/dock/": "console.pending.dock",
    "/troubleshooting/": "console.pending.troubleshooting",
    "/timemachine/": "console.pending.timemachine",
}


@router.get(PATH, include_in_schema=False)
def pending(request: Request) -> JSONResponse:
    if current_session(request) is None:
        return JSONResponse({})
    t = page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    ).t
    found = request.app.state.pending_counts(request.app.state.generated_dir)
    return JSONResponse(
        {path: {"count": count, "text": t(TEXTS[path], count=count)} for path, count in found.items() if path in TEXTS}
    )


# Injected before `</body>` for a signed-in person on both listeners: on a
# page with console cards it fetches `/pending` and draws the badges,
# elsewhere it does nothing. The console page itself stays script-free.
SNIPPET = """<style>
.card[data-pending] { position: relative; }
.pending-mark { position: absolute; top: .55rem; right: .6rem; min-width: 1.4rem; height: 1.4rem; padding: 0 .35rem; box-sizing: border-box; border-radius: .7rem; background: #c2410c; color: #fff; font: 700 .78rem/1.4rem system-ui, sans-serif; text-align: center; box-shadow: 0 0 0 2px #fff; }
</style>
<script>
(function () {
  var cards = document.querySelectorAll("a.card[data-pending]");
  if (!cards.length || !window.fetch) { return; }
  fetch("/pending" + window.location.search, { credentials: "same-origin", headers: { "Accept": "application/json" } })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .then(function (found) {
      cards.forEach(function (card) {
        var item = found[card.getAttribute("data-pending")];
        if (!item || !item.count) { return; }
        var mark = document.createElement("span");
        mark.className = "pending-mark"; mark.textContent = item.count;
        mark.title = item.text; mark.setAttribute("aria-label", item.text);
        card.appendChild(mark);
        card.title = item.text + " \\u2014 " + card.title;
      });
    })
    .catch(function () {});
})();
</script>
"""
