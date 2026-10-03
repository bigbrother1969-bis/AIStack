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

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from aistack.i18n import Languages, default_languages
from aistack.priority.screen import Discover, discover_containers
from aistack.kernel.bootstrap import create_kernel
from aistack.selection.screen import SyncthingStatus, read_syncthing
from aistack.troubleshooting.findings import CollectFindings, qualified_findings
from aistack.troubleshooting.guide import AskAI, ask_ollama
from aistack.timemachine.screen import ExpiringValue, live_network_tree
from aistack.timemachine.tree import NetworkTreeNode
from aistack.web import console, network_discovery, priority, selection, timemachine, troubleshooting
from aistack.web.exposure import Listeners, include


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class WebPaths:
    """The declaration files the screens read and write, one per screen."""

    network_discovery: Path = (
        PACKAGE_ROOT / "network_discovery" / "definitions" / "network_discovery.yml"
    )
    resource_priority: Path = PACKAGE_ROOT / "priority" / "definitions" / "resource_priority.yml"
    selection: Path = PACKAGE_ROOT / "selection" / "definitions" / "music_android.yml"
    topology: Path = (
        PACKAGE_ROOT / "architecture" / "definitions" / "infrastructure_topology.yml"
    )
    # What a definition's repository-relative paths (`selection_file`)
    # resolve against: the checkout the application runs from.
    repository_root: Path = PACKAGE_ROOT.parents[1]


def create_app(
    generated_dir: Path,
    listeners: Listeners,
    languages: Languages | None = None,
    paths: WebPaths | None = None,
    discover: Discover = discover_containers,
    syncthing: SyncthingStatus = read_syncthing,
    kernel: Any = None,
    collect_findings: CollectFindings = qualified_findings,
    ask_ai: AskAI = ask_ollama,
    run_in_background: Callable[[Callable[[], None]], Any] | None = None,
    network_tree: Callable[[], list[NetworkTreeNode]] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="AIStack",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # No automatic `/screen` → `/screen/` redirect: the router answers
    # it before any route — and so before any exposure guard — runs,
    # and a redirect on the public port would tell apart a LAN screen
    # from a path that does not exist. Each screen declares both forms.
    app.router.redirect_slashes = False
    app.state.generated_dir = generated_dir
    app.state.listeners = listeners
    app.state.languages = languages if languages is not None else default_languages()
    app.state.paths = paths if paths is not None else WebPaths()
    # Host-touching collaborators (ADR-0012 § 4): what Docker reports.
    app.state.discover_containers = discover
    # ... and what Syncthing reports for the Selection UI's folder.
    app.state.syncthing = syncthing
    app.state.kernel = kernel if kernel is not None else create_kernel()
    # ... the host's findings, and the AI Runtime, for the assistant.
    app.state.collect_findings = collect_findings
    app.state.ask_ai = ask_ai
    app.state.troubleshooting_sessions = {}
    # One worker: the model answers one call at a time on this host,
    # and a diagnosis must not hold a request open for minutes.
    app.state.run_in_background = (
        run_in_background
        if run_in_background is not None
        else ThreadPoolExecutor(max_workers=1, thread_name_prefix="aistack-ai").submit
    )
    # ... and the live network tree the Time Machine draws, rebuilt at
    # most every 45 s: live Docker discovery is slow per request.
    app.state.network_tree = (
        network_tree
        if network_tree is not None
        else ExpiringValue(
            lambda: live_network_tree(
                app.state.kernel,
                generated_dir,
                app.state.paths.topology,
                app.state.paths.network_discovery,
            )
        ).get
    )
    app.state.routers = []

    include(app, console.router)
    include(app, network_discovery.router, network_discovery.PREFIX)
    include(app, priority.router, priority.PREFIX)
    include(app, selection.router, selection.PREFIX)
    include(app, troubleshooting.router, troubleshooting.PREFIX)
    include(app, timemachine.router, timemachine.PREFIX)

    @app.exception_handler(StarletteHTTPException)
    async def _localized_error(request: Request, error: StarletteHTTPException) -> Response:
        # A path no router knows, and a route refused on this port, are
        # the same answer: the console's own localized 404 — a refused
        # route must not be told apart from one that does not exist.
        if error.status_code == 404:
            return console.answer(request, console.NOT_FOUND_PATH)

        return Response(status_code=error.status_code)

    return app
