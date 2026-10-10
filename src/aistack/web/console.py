"""Console routes (ADR-0012 § 1, ADR-0010 § 5).

A thin adapter over `aistack.console.routing.respond`, which computes
every answer. The paths are stable because the reverse proxy and
bookmarks point at them. All routes are `PUBLIC`.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from aistack.console.routing import PAGES, READING_PATHS, SETTINGS_PATH, respond
from aistack.web.authentication import SIGNED_IN_ONLY
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
    """`respond` for this request as a Starlette response.

    `path` overrides the request path; the query is kept so `?lang=`
    still chooses the language.
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


# The two pages that describe the infrastructure need a session
# (ADR-0014 § 5); the console, Settings and the reading pages do not.
SIGNED_IN_PATHS = ("/architecture.html", "/health.html", "/plan.html")

for _path in CONSOLE_PATHS:
    router.add_api_route(
        _path,
        _console_route,
        methods=["GET", "HEAD"],
        include_in_schema=False,
        dependencies=[SIGNED_IN_ONLY] if _path in SIGNED_IN_PATHS else [],
    )
