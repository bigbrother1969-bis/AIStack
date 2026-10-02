"""
`create_app` — AIStack's single web application (`ADR-0012` § 1).

Everything the application reads from its host arrives as an argument,
so the suite builds it with a temporary directory and fakes, and every
route is exercised in process, never over a socket.

FastAPI's own `/docs`, `/redoc` and `/openapi.json` are switched off:
they are routes too, and none of them declares an exposure — left on,
they would describe every LAN route on the public port.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from aistack.i18n import Languages, default_languages
from aistack.web import console
from aistack.web.exposure import Listeners, include


def create_app(
    generated_dir: Path,
    listeners: Listeners,
    languages: Languages | None = None,
) -> FastAPI:
    app = FastAPI(
        title="AIStack",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.generated_dir = generated_dir
    app.state.listeners = listeners
    app.state.languages = languages if languages is not None else default_languages()
    app.state.routers = []

    include(app, console.router)

    @app.exception_handler(StarletteHTTPException)
    async def _localized_error(request: Request, error: StarletteHTTPException) -> Response:
        # A path no router knows, and a route refused on this port, are
        # the same answer: the console's own localized 404 — a refused
        # route must not be told apart from one that does not exist.
        if error.status_code == 404:
            return console.answer(request, console.NOT_FOUND_PATH)

        return Response(status_code=error.status_code)

    return app
