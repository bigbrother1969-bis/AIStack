"""
The console's routes inside AIStack's single web application
(`ADR-0012` § 1, `ADR-0010` § 5).

A thin adapter: every answer is computed by
`aistack.console.routing.respond`, a pure function the suite already
tests route by route; this router only hands it the request line and
the cookie and copies its status, headers and body onto the wire. The
paths are the ones the standard-library server answered since
2026-09-27, so the Nginx Proxy Manager entry for
`aistack.persiaut-family.fr` and every bookmark keep working.

Every route here is `PUBLIC`: the console, its two generated pages and
Settings are what the public port exists for.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from aistack.console.routing import PAGES, READING_PATHS, SETTINGS_PATH, respond
from aistack.web.exposure import PUBLIC

router = APIRouter(dependencies=[PUBLIC])

CONSOLE_PATHS = (
    "/",
    "/index.html",
    SETTINGS_PATH,
    *READING_PATHS,
    *(f"/{page}" for page in PAGES),
)


NOT_FOUND_PATH = "/.not-found"


def answer(request: Request, path: str | None = None) -> Response:
    """
    `respond`, for this request, as a Starlette response — for `path`
    instead of the request's own when one is given, keeping the query
    so a `?lang=` still chooses the language of the answer.
    """

    target = path if path is not None else request.url.path

    if request.url.query:
        target += f"?{request.url.query}"

    computed = respond(
        request.method,
        target,
        request.headers.get("cookie"),
        request.app.state.generated_dir,
        request.app.state.languages,
    )

    response = Response(content=computed.body, status_code=computed.status)
    del response.headers["content-length"]

    for name, value in computed.headers:
        response.headers.append(name, value)

    return response


def _console_route(request: Request) -> Response:
    return answer(request)


for _path in CONSOLE_PATHS:
    router.add_api_route(
        _path,
        _console_route,
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )
