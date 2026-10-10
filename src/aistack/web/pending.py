"""
`/pending` — what waits for the owner behind each console card (the
owner, 2026-10-10: "des petites pastilles de couleur sur les cartes
pour lesquelles il y a des actions en attente"). LAN only, signed in:
the console asks it and puts a pastille on the card whose screen has
something to do.

    {"/dock/": {"count": 1, "text": "1 mise à jour à valider"}, ...}

Counted live, from what the screens themselves read:
- the dock: proposals waiting for an administrator's validation;
- the troubleshooting assistant: the Health Cockpit's findings, as the
  vigil's last pass saw them (`health-state.json`);
- the Time Machine: Explications proposed and not yet validated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import page_language
from aistack.web.authentication import current_session
from aistack.web.exposure import LAN_ONLY

PATH = "/pending"

router = APIRouter(dependencies=[LAN_ONLY])


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
