"""Which port a route answers on (ADR-0012 § 3).

The process listens on two ports: the public one, the only one the
reverse proxy points at, and the LAN one, which no proxy host names.

The decision uses the port the request arrived on
(`request.scope["server"]`), never a header a client could forge. A
request on any other port is refused.

Each router declares exactly one of `PUBLIC` or `LAN_ONLY`; `include`
enforces this and is the only way `create_app` adds routes.
`tests/unit/web/test_every_route_declares_its_exposure.py` checks that
every route's guard actually runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request


@dataclass(frozen=True)
class Listeners:
    """The two ports one process serves (`ADR-0012` § 3)."""

    public_port: int
    lan_port: int

    def __post_init__(self) -> None:
        if self.public_port == self.lan_port:
            raise ValueError(
                f"the public and LAN listeners share port {self.public_port}: "
                "the exposure of a route would no longer be decided by its port"
            )


def arrival_port(request: Request) -> int | None:
    """The local port this request reached, or `None` when unknown."""

    server = request.scope.get("server")

    if not server:
        return None

    return int(server[1])


def serve_publicly(request: Request) -> None:
    """A route answered on both listeners."""

    listeners: Listeners = request.app.state.listeners

    if arrival_port(request) not in (listeners.public_port, listeners.lan_port):
        raise HTTPException(status_code=404)


def serve_on_lan_only(request: Request) -> None:
    """A route answered on the LAN listener and nowhere else."""

    listeners: Listeners = request.app.state.listeners

    if arrival_port(request) != listeners.lan_port:
        raise HTTPException(status_code=404)


PUBLIC = Depends(serve_publicly)
LAN_ONLY = Depends(serve_on_lan_only)

EXPOSURE_GUARDS = (serve_publicly, serve_on_lan_only)


def guard_of(router: APIRouter) -> object:
    """The one exposure guard `router` declares; refuses none or two."""

    guards = [
        dependency.dependency
        for dependency in router.dependencies
        if dependency.dependency in EXPOSURE_GUARDS
    ]

    if len(guards) != 1:
        raise ValueError(
            f"a router must declare exactly one exposure (PUBLIC or LAN_ONLY), found {len(guards)}"
        )

    return guards[0]


def include(app: FastAPI, router: APIRouter, prefix: str = "") -> None:
    """Add `router` to `app`, after checking where it may answer."""

    guard = guard_of(router)
    app.include_router(router, prefix=prefix)
    app.state.routers.append((prefix, router, guard))
