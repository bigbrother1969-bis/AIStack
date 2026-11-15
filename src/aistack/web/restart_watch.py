"""*Relance au démarrage*: the containers found stuck after a start, and what was done. LAN only.

A reading screen over what `aistack.cli.restart_watch` writes
(`restart-watch.jsonl`, `restart-watch-state.json`) and the owner's
declaration. It restarts nothing and writes nothing: the decisions are
the watch's, the declaration is edited in Settings, with the others.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.restart_watch import journal
from aistack.restart_watch.load import load_restart_watch_yaml
from aistack.web.authentication import SIGNED_IN_ONLY
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/restart-watch"
SHOWN = 100

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    language = _language(request)
    directory = request.app.state.generated_dir
    definition = load_restart_watch_yaml(request.app.state.paths.restart_watch)
    state = journal.read_state(directory)

    context: dict[str, object] = {
        "base": PREFIX,
        "definition": definition,
        "state": state,
        "stuck": state.get("stuck") or [],
        "entries": journal.read(directory, SHOWN),
        **language.context(),
    }

    response = templates.TemplateResponse(
        request=request, name="restart_watch/index.html", context=context
    )

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response
