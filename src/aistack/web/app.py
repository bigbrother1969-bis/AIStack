"""`create_app`: AIStack's single web application (ADR-0012 § 1).

Everything read from the host is an argument, so tests build the app
with a temporary directory and fakes and exercise routes in process.

FastAPI's `/docs`, `/redoc` and `/openapi.json` are off: they declare no
exposure and would describe every LAN route on the public port.
"""

from __future__ import annotations

from aistack.config import config_dir, configured

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from functools import partial
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER, Languages, default_languages
from aistack.i18n.web import page_language
from aistack.priority.screen import Discover, discover_containers
from aistack.kernel.bootstrap import create_kernel
from aistack.selection.screen import SyncthingStatus, read_syncthing
from aistack.troubleshooting.findings import CollectFindings, qualified_findings
from aistack.ai_runtime.call_journal import PORTAL_CHAT, SECURITY_PAGE, TROUBLESHOOTING, journaled
from aistack.portal import chat as portal_chat
from aistack.troubleshooting.guide import AskAI, ai_destination, ask_managed
from aistack.timemachine.screen import ExpiringValue, live_network_tree
from aistack.timemachine.tree import NetworkTreeNode
from aistack.web import (
    arrivals,
    authentication,
    console,
    first_start,
    network_discovery,
    priority,
    restart_watch,
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
from aistack.web import boot_check as boot_check_screen
from aistack.web import ai_engines as ai_engines_screen
from aistack.web import footprint as footprint_screen
from aistack.web import ask as ask_screen
from aistack.web import security as security_screen
from aistack.web import setup_wizard as setup_wizard_screen
from aistack.instance.setup_wizard import apply_sign_in
from aistack.instance.setup_wizard import probe as setup_probe
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
    # The arrivals' declaration and the file a click declares a container
    # in (ADR-0026).
    arrivals: Path = configured(PACKAGE_ROOT / "arrivals" / "definitions" / "arrivals.yml")
    categorization: Path = configured(PACKAGE_ROOT / "architecture" / "definitions" / "service_categorization.yml")
    # The restart watch's declaration, shown by its screen (ADR-0025).
    restart_watch: Path = configured(PACKAGE_ROOT / "restart_watch" / "definitions" / "restart_watch.yml")
    # Read by the troubleshooting assistant to describe a finding.
    backup_strategy: Path = configured(PACKAGE_ROOT / "backup_strategy" / "definitions" / "backup_strategy.yml")
    pra_tests: Path = configured(PACKAGE_ROOT / "pra" / "definitions" / "pra_tests.yml")
    selection: Path = configured(PACKAGE_ROOT / "selection" / "definitions" / "music_android.yml")
    # The generalized sync's contents and destinations (ADR-0022).
    sync: Path = configured(PACKAGE_ROOT / "sync" / "definitions" / "sync.yml")
    topology: Path = (
        configured(PACKAGE_ROOT / "architecture" / "definitions" / "infrastructure_topology.yml")
    )
    # Base for relative paths in definitions (`selection_file`): the
    # configuration directory in the container (ADR-0017), else the checkout.
    repository_root: Path = config_dir() or PACKAGE_ROOT.parents[1]
    # Where the data is to be moved, chosen from Settings.
    data_location: Path = location_file(config_dir(), PACKAGE_ROOT.parents[1])


def create_app(
    generated_dir: Path,
    listeners: Listeners,
    languages: Languages | None = None,
    paths: WebPaths | None = None,
    discover: Discover | None = None,
    syncthing: SyncthingStatus = read_syncthing,
    kernel: Any = None,
    collect_findings: CollectFindings | None = None,
    ask_ai: AskAI | None = None,
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
    security_window: Callable[..., dict[str, Any]] | None = None,
    ask_local_ai: AskAI | None = None,
    local_model: Callable[[], str] | None = None,
    engine_starting: Callable[[], str] | None = None,
    ask_portal: AskAI | None = None,
    portal_destination: Callable[[], Any] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="AIStack",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # No automatic `/screen` → `/screen/` redirect: it would run before the
    # exposure guard and reveal LAN screens on the public port. Each screen
    # declares both forms.
    app.router.redirect_slashes = False
    app.state.generated_dir = generated_dir
    # What waits behind each console card.
    app.state.pending_counts = pending_counts if pending_counts is not None else pending_screen.counts
    # API keys entered from Settings, laid over the environment; both
    # callables are replaced in tests.
    app.state.api_keys = api_keys if api_keys is not None else load_api_keys
    app.state.test_api_key = test_api_key if test_api_key is not None else api_keys_screen.test_key
    apply_to_environ(generated_dir, app.state.api_keys())
    app.state.listeners = listeners
    # The host's disks and mounts, for Settings.
    app.state.storage = storage if storage is not None else live_storage
    app.state.instance_config = load_instance_config_yaml(INSTANCE_CONFIG)
    # Development or production (ADR-0016): which Explication rules apply.
    app.state.phase = phase if phase is not None else app.state.instance_config.phase
    app.state.languages = languages if languages is not None else default_languages()
    app.state.paths = paths if paths is not None else WebPaths()
    # Host-touching collaborators (ADR-0012 § 4): what Docker reports.
    # By default through the providers of this application's own Kernel,
    # not a Kernel booted per call (ADR-0027 § 9).
    app.state.kernel = kernel if kernel is not None else create_kernel()
    providers = app.state.kernel.registries.providers
    app.state.discover_containers = (
        discover if discover is not None else partial(discover_containers, providers)
    )
    # ... and what Syncthing reports for the Selection folder.
    app.state.syncthing = syncthing
    # ... the host's findings and the AI runtime, for the assistant.
    app.state.collect_findings = (
        collect_findings if collect_findings is not None else partial(qualified_findings, providers)
    )
    # Every question to a model is written to the journal under its caller (ADR-0029), without its content.
    journal = generated_dir / "ai-calls"
    app.state.ask_ai = journaled(ask_ai or partial(ask_managed, TROUBLESHOOTING), TROUBLESHOOTING, journal)
    # Where the AI's question goes, shown before the click.
    app.state.ai_destination = destination
    app.state.troubleshooting_sessions = {}
    # The security screen (ADR-0028 T4b): its window goes through the Runtime, its AI is the local engine only.
    app.state.security_window = security_window if security_window is not None else security_screen.run_window
    app.state.ask_local_ai = journaled(ask_local_ai or partial(ask_managed, SECURITY_PAGE), SECURITY_PAGE, journal)
    app.state.local_model = local_model if local_model is not None else security_screen.local_model
    app.state.engine_starting = engine_starting if engine_starting is not None else security_screen.engine_starting
    app.state.security_sessions = {}
    # The page for everyone (ADR-0029 § 12): a question typed there is held in memory only, never written.
    app.state.ask_portal = journaled(ask_portal or partial(ask_managed, PORTAL_CHAT), PORTAL_CHAT, journal)
    app.state.portal_destination = portal_destination if portal_destination is not None else portal_chat.destination
    app.state.portal_exchanges = portal_chat.Exchanges()
    # The CPU findings last listed: a reading is an instant, so the one
    # clicked may be gone a second later.
    app.state.troubleshooting_listed = {}
    # AI jobs per person, for the "answer ready" notice.
    app.state.ai_jobs = AIJobs()
    # One worker: the model answers one call at a time on this host, and a
    # diagnosis must not hold a request open for minutes.
    app.state.run_in_background = (
        run_in_background
        if run_in_background is not None
        else ThreadPoolExecutor(max_workers=1, thread_name_prefix="aistack-ai").submit
    )
    # ... and the live network tree, rebuilt at most every 45 s because
    # live Docker discovery is slow.
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
    # Sign-in secrets kept by the installation assistant (ADR-0023 § 5),
    # applied to the environment before authentication reads it.
    apply_sign_in(generated_dir)
    # Sign-in (ADR-0013): Pocket ID, sessions on disk, fallback administrator.
    app.state.authentication = (
        auth
        if auth is not None
        else build_authentication(
            generated_dir,
            app.state.instance_config.service_url("web_lan"),
        )
    )
    # What a new installation still has to declare (ADR-0017 § 4), measured
    # once: nothing it reads changes before a restart.
    app.state.first_start = pending if pending is not None else first_start.measured(app.state.authentication, generated_dir)
    # The installation assistant's probe of the public addresses (ADR-0023 § 5).
    app.state.setup_probe = setup_probe
    app.state.routers = []

    include(app, console.router)
    include(app, first_start.router)
    include(app, setup_wizard_screen.router)
    include(app, storage_screen.router)
    include(app, declarations_screen.router)
    include(app, api_keys_screen.router)
    include(app, authentication.router)
    include(app, authentication.lan_router)
    include(app, network_discovery.router, network_discovery.PREFIX)
    include(app, priority.router, priority.PREFIX)
    include(app, arrivals.router, arrivals.PREFIX)
    include(app, restart_watch.router, restart_watch.PREFIX)
    include(app, selection.router, selection.PREFIX)
    include(app, troubleshooting.router, troubleshooting.PREFIX)
    include(app, security_screen.router, security_screen.PREFIX)
    include(app, ai_engines_screen.router, ai_engines_screen.PREFIX)
    include(app, ask_screen.router, ask_screen.PREFIX)
    include(app, footprint_screen.router, footprint_screen.PREFIX)
    include(app, timemachine.router, timemachine.PREFIX)
    include(app, dock_screen.router, dock_screen.PREFIX)
    include(app, health.router)
    include(app, notifications.router)
    include(app, pending_screen.router)
    include(app, boot_check_screen.router, boot_check_screen.PREFIX)
    include(app, boot_check_screen.state_router)

    @app.middleware("http")
    async def _who_is_signed_in(request: Request, call_next: Any) -> Response:
        # Fills the navigation's session marker on every HTML page with the
        # signed-in person or the sign-in link (ADR-0013 § 7).
        response: Response = await call_next(request)
        # A HEAD answer has no body to fill.
        if request.method == "HEAD" or not response.headers.get("content-type", "").startswith(
            "text/html"
        ):
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])  # type: ignore[attr-defined]
        # While something required is undeclared, every page links to /setup
        # (ADR-0017 § 4), just before the sign-in link.
        marker = SESSION_MARKER.encode("ascii")
        if marker in body:
            body = body.replace(marker, first_start.badge(request).encode("utf-8") + marker, 1)
        filled = fill_markers(request, body)
        filled = _with_notices(request, filled)
        rebuilt = Response(content=filled, status_code=response.status_code)
        # Keep every header (each `set-cookie` separately) except the length.
        rebuilt.raw_headers = [
            (name, value) for name, value in response.raw_headers if name.lower() != b"content-length"
        ] + [(b"content-length", str(len(filled)).encode("ascii"))]
        return rebuilt

    # Rights (ADR-0014 § 2): no session, sign in; no right, a 403.
    app.add_exception_handler(SignInRequired, answer_sign_in_required)  # type: ignore[arg-type]
    app.add_exception_handler(Refused, answer_refused)  # type: ignore[arg-type]

    @app.exception_handler(StarletteHTTPException)
    async def _localized_error(request: Request, error: StarletteHTTPException) -> Response:
        # An unknown path and a route refused on this port get the same localized
        # 404, so a refused route cannot be told apart from a missing one.
        if error.status_code == 404:
            return console.answer(request, console.NOT_FOUND_PATH)

        return Response(status_code=error.status_code)

    return app


def _with_notices(request: Request, body: bytes) -> bytes:
    """Insert the badges script, and on the LAN listener the AI notice, before `</body>`.

    Signed-in sessions only; AI screens answer on the LAN listener only.
    """

    listeners: Listeners = request.app.state.listeners
    if current_session(request) is None:
        return body
    end = body.rfind(b"</body>")
    if end < 0:
        return body
    # The cards' badges, on both listeners.
    added = pending_screen.SNIPPET + boot_check_screen.SNIPPET
    if arrival_port(request) == listeners.lan_port:
        language = page_language(
            request.query_params.get(LANGUAGE_PARAMETER),
            request.cookies.get(LANGUAGE_COOKIE),
            request.app.state.languages,
        )
        added = notifications.snippet(language.t) + added
    return body[:end] + added.encode("utf-8") + body[end:]
