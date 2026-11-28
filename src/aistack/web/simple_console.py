"""La console simplifiée pour l'utilisateur non-admin (ADR-0033).

Ce lot (CN0) n'est qu'un squelette : un gabarit minimal, aucune donnée
réelle branchée. CN1 y met la maquette (variante C, valeurs figées).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from aistack.web.authentication import SIGNED_IN_ONLY
from aistack.web.exposure import PUBLIC
from aistack.web.templating import templates

PREFIX = "/simple"

# Like Architecture and the Health cockpit (ADR-0014 § 5), not like the
# bare console: this screen shows the same infrastructure status
# (security, backups, disk, updates), so it needs a session too.
router = APIRouter(dependencies=[PUBLIC, SIGNED_IN_ONLY])


def _index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="simple_console/index.html",
        context={},
    )


# Both forms declared explicitly: `app.router.redirect_slashes` is off
# (`aistack.web.app.create_app`), so a screen must answer both itself.
router.add_api_route("", _index, methods=["GET", "HEAD"], include_in_schema=False)
router.add_api_route("/", _index, methods=["GET", "HEAD"], include_in_schema=False)
