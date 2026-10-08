"""
`/healthz` — is the web process answering (1.10): what Docker's
healthcheck asks (`python -m aistack.cli.healthcheck`), so `docker ps`,
and a dashboard reading Docker such as Homepage, show the container
`healthy` rather than only `running`.

On the local-network listener only, no session: it says `ok` when the
data directory the screens read is there, `503` when it is not (a
moved or unmounted `AISTACK_DATA_DIR`) — nothing else about the host.
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
