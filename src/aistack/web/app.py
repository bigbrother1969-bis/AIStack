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

from aistack.config import config_dir, configured

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER, Languages, default_languages
from aistack.i18n.web import page_language
from aistack.priority.screen import Discover, discover_containers
from aistack.kernel.bootstrap import create_kernel
from aistack.selection.screen import SyncthingStatus, read_syncthing
from aistack.troubleshooting.findings import CollectFindings, qualified_findings
from aistack.troubleshooting.guide import AskAI, ai_destination, ask_ai_runtime
from aistack.timemachine.screen import ExpiringValue, live_network_tree
from aistack.timemachine.tree import NetworkTreeNode
from aistack.web import (
    authentication,
    console,
    first_start,
    network_discovery,
    priority,
    selection,
    timemachine,
    troubleshooting,
)
from aistack.instance.yaml.store import load_instance_config_yaml
from aistack.web.storage import live_storage
from aistack.web import storage as storage_screen
from aistack.web import declarations as declarations_screen
from aistack.web import api_keys as api_keys_screen
from aistack.api_keys import apply_to_environ, load_api_keys
from aistack.web import dock as dock_screen
from aistack.web import health
from aistack.web import notifications
from aistack.web import pending as pending_screen
from aistack.web.ai_jobs import AIJobs
from aistack.instance.data_location import location_file
from aistack.web.authentication import (
    Authentication,
    Refused,
    SignInRequired,
    answer_refused,
    answer_sign_in_required,
    build_authentication,
    current_session,
    fill_markers,
)
from aistack.web.exposure import Listeners, arrival_port, include
from aistack.renderers.nav import SESSION_MARKER


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
INSTANCE_CONFIG = configured(PACKAGE_ROOT / "instance" / "definitions" / "instance_config.yml")


@dataclass(frozen=True)
class WebPaths:
    """The declaration files the screens read and write, one per screen."""

    network_discovery: Path = (
        configured(PACKAGE_ROOT / "network_discovery" / "definitions" / "network_discovery.yml")
    )
    resource_priority: Path = configured(PACKAGE_ROOT / "priority" / "definitions" / "resource_priority.yml")
    # What the troubleshooting assistant states of a finding (2026-10-09).
    backup_strategy: Path = configured(PACKAGE_ROOT / "backup_strategy" / "definitions" / "backup_strategy.yml")
    pra_tests: Path = configured(PACKAGE_ROOT / "pra" / "definitions" / "pra_tests.yml")
    selection: Path = configured(PACKAGE_ROOT / "selection" / "definitions" / "music_android.yml")
    # The generalized sync's contents and destinations (ADR-0022).
    sync: Path = configured(PACKAGE_ROOT / "sync" / "definitions" / "sync.yml")
    topology: Path = (
        configured(PACKAGE_ROOT / "architecture" / "definitions" / "infrastructure_topology.yml")
    )
    # What a definition's relative paths (`selection_file`) resolve
    # against: the configuration directory when there is one (the
    # container, ADR-0017), else the checkout the application runs from.
    repository_root: Path = config_dir() or PACKAGE_ROOT.parents[1]
    # Where the data is to be moved (1.8): chosen from Settings.
    data_location: Path = location_file(config_dir(), PACKAGE_ROOT.parents[1])


def create_app(
    generated_dir: Path,
    listeners: Listeners,
    languages: Languages | None = None,
    paths: WebPaths | None = None,
    discover: Discover = discover_containers,
    syncthing: SyncthingStatus = read_syncthing,
    kernel: Any = None,
    collect_findings: CollectFindings = qualified_findings,
    ask_ai: AskAI = ask_ai_runtime,
    destination: Callable[[], tuple[str, str]] = ai_destination,
    run_in_background: Callable[[Callable[[], None]], Any] | None = None,
    network_tree: Callable[[], list[NetworkTreeNode]] | None = None,
    auth: Authentication | None = None,
    phase: str | None = None,
    storage: Callable[[Path], Any] | None = None,
    pending: list[Any] | None = None,
    api_keys: Callable[[], Any] | None = None,
    test_api_key: Callable[[str], str | None] | None = None,
    pending_counts: Callable[[Path], dict[str, int]] | None = None,
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
    # What waits behind each console card (2026-10-10).
    app.state.pending_counts = pending_counts if pending_counts is not None else pending_screen.counts
    # The API keys entered from Settings, laid over the environment
    # (2026-10-09); `api_keys` and `test_api_key` are replaced in tests.
    app.state.api_keys = api_keys if api_keys is not None else load_api_keys
    app.state.test_api_key = test_api_key if test_api_key is not None else api_keys_screen.test_key
    apply_to_environ(generated_dir, app.state.api_keys())
    app.state.listeners = listeners
    # The host's disks and mounts, for Settings (2026-10-04).
    app.state.storage = storage if storage is not None else live_storage
    app.state.instance_config = load_instance_config_yaml(INSTANCE_CONFIG)
    # Development or production (ADR-0016): which Explication rules apply.
    app.state.phase = phase if phase is not None else app.state.instance_config.phase
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
    # Where the AI's question goes, said before the click (2026-10-09).
    app.state.ai_destination = destination
    app.state.troubleshooting_sessions = {}
    # The CPU findings the list last showed, and when: a reading is an
    # instant, so the one the owner clicked may be gone a second later.
    app.state.troubleshooting_listed = {}
    # What the AI is working on, for whom: the notice on every page
    # when an answer is ready (2026-10-09).
    app.state.ai_jobs = AIJobs()
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
    # Who is signed in (ADR-0013): Pocket ID, the sessions on disk
    # under the generated directory, the fallback administrator.
    app.state.authentication = (
        auth
        if auth is not None
        else build_authentication(
            generated_dir,
            app.state.instance_config.service_url("web_lan"),
        )
    )
    # What a new installation still has to declare (ADR-0017 § 4),
    # measured once: nothing it reads changes before a restart.
    app.state.first_start = pending if pending is not None else first_start.measured(app.state.authentication)
    app.state.routers = []

    include(app, console.router)
    include(app, first_start.router)
    include(app, storage_screen.router)
    include(app, declarations_screen.router)
    include(app, api_keys_screen.router)
    include(app, authentication.router)
    include(app, authentication.lan_router)
    include(app, network_discovery.router, network_discovery.PREFIX)
    include(app, priority.router, priority.PREFIX)
    include(app, selection.router, selection.PREFIX)
    include(app, troubleshooting.router, troubleshooting.PREFIX)
    include(app, timemachine.router, timemachine.PREFIX)
    include(app, dock_screen.router, dock_screen.PREFIX)
    include(app, health.router)
    include(app, notifications.router)
    include(app, pending_screen.router)

    @app.middleware("http")
    async def _who_is_signed_in(request: Request, call_next: Any) -> Response:
        # Every HTML page carries the navigation's session marker;
        # this writes the signed-in person — or the way to sign in —
        # into it, generated pages and screens alike (ADR-0013 § 7).
        response: Response = await call_next(request)
        # A HEAD answer has no body to fill: its headers stay those of
        # the page as generated.
        if request.method == "HEAD" or not response.headers.get("content-type", "").startswith(
            "text/html"
        ):
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])  # type: ignore[attr-defined]
        # While something required is undeclared, every page leads to
        # what (ADR-0017 § 4), just before the way to sign in.
        marker = SESSION_MARKER.encode("ascii")
        if marker in body:
            body = body.replace(marker, first_start.badge(request).encode("utf-8") + marker, 1)
        filled = fill_markers(request, body)
        filled = _with_notices(request, filled)
        rebuilt = Response(content=filled, status_code=response.status_code)
        # Every header as it was — each `set-cookie` on its own — but the
        # length, which the filled body changes.
        rebuilt.raw_headers = [
            (name, value) for name, value in response.raw_headers if name.lower() != b"content-length"
        ] + [(b"content-length", str(len(filled)).encode("ascii"))]
        return rebuilt

    # Rights (ADR-0014 § 2): no session, sign in; no right, a 403.
    app.add_exception_handler(SignInRequired, answer_sign_in_required)  # type: ignore[arg-type]
    app.add_exception_handler(Refused, answer_refused)  # type: ignore[arg-type]

    @app.exception_handler(StarletteHTTPException)
    async def _localized_error(request: Request, error: StarletteHTTPException) -> Response:
        # A path no router knows, and a route refused on this port, are
        # the same answer: the console's own localized 404 — a refused
        # route must not be told apart from one that does not exist.
        if error.status_code == 404:
            return console.answer(request, console.NOT_FOUND_PATH)

        return Response(status_code=error.status_code)

    return app


def _with_notices(request: Request, body: bytes) -> bytes:
    """The AI notice (`aistack.web.notifications`) before `</body>`, on
    the local-network listener and for a signed-in person only — the
    screens that ask the AI answer there and nowhere else."""

    listeners: Listeners = request.app.state.listeners
    if arrival_port(request) != listeners.lan_port or current_session(request) is None:
        return body
    end = body.rfind(b"</body>")
    if end < 0:
        return body
    language = page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )
    return body[:end] + notifications.snippet(language.t).encode("utf-8") + body[end:]
