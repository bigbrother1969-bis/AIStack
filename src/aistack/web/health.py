"""`/healthz`: the probe behind Docker's healthcheck (`aistack.cli.healthcheck`).

LAN listener only, no session. Answers `ok` when the data directory exists,
`503` when it does not (e.g. an unmounted `AISTACK_DATA_DIR`).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from aistack.web.exposure import LAN_ONLY

PATH = "/healthz"

router = APIRouter(dependencies=[LAN_ONLY])


@router.get(PATH, response_class=PlainTextResponse, include_in_schema=False)
def healthz(request: Request) -> PlainTextResponse:
    if not request.app.state.generated_dir.is_dir():
        return PlainTextResponse("data directory unreachable\n", status_code=503)
    return PlainTextResponse("ok\n")
