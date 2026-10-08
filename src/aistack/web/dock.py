"""
*Quai* — governed changes (`ADR-0019` § 3). LAN only, signed in; the
actions — propose, validate, reject — for an administrator, bound to
the session. Nothing here changes a service: a validated proposal is
executed by the dock on the host.

Docker and the registry reach the route through `app.state`
(`dock_runner`, `dock_publisher`), so a test replaces them.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.dock import proposals
from aistack.dock.candidates import Candidate, inspect_all
from aistack.dock.declaration import load_dock_declaration
from aistack.dock.registry import published_digest
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.sandbox.run import docker_runner
from aistack.web.authentication import ADMIN_ACTION, SIGNED_IN_ONLY, current_session
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/dock"

# Literal keys, so the catalog test sees every one of them.
STATUS_KEYS = {
    proposals.PROPOSED: "dock.status_label.proposed",
    proposals.VALIDATED: "dock.status_label.validated",
    proposals.REJECTED: "dock.status_label.rejected",
    proposals.RUNNING: "dock.status_label.running",
    proposals.APPLIED: "dock.status_label.applied",
    proposals.FAILED: "dock.status_label.failed",
    proposals.ROLLED_BACK: "dock.status_label.rolled_back",
}
OPERATION_KEYS = {
    "preconditions": "dock.operation.preconditions",
    "sandbox restore": "dock.operation.sandbox_restore",
    "fetch": "dock.operation.fetch",
    "rehearsal": "dock.operation.rehearsal",
    "keep": "dock.operation.keep",
    "apply": "dock.operation.apply",
    "live checks": "dock.operation.live_checks",
    "rollback": "dock.operation.rollback",
    "live checks after rollback": "dock.operation.live_checks_after_rollback",
}
OPERATION_STATUS_KEYS = {
    "running": "dock.operation_status.running",
    "done": "dock.operation_status.done",
    "failed": "dock.operation_status.failed",
}
REFUSED_KEYS = (
    "dock.refused.unknown", "dock.refused.why", "dock.refused.nothing", "dock.refused.open",
    "dock.refused.not_proposed", "dock.refused.same_person", "dock.refused.closed",
)

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def _candidates(request: Request) -> list[Candidate]:
    runner = getattr(request.app.state, "dock_runner", docker_runner)
    publisher = getattr(request.app.state, "dock_publisher", published_digest)
    return inspect_all(load_dock_declaration(), runner, publisher)


def _who(request: Request) -> str:
    session = current_session(request)
    if session is None:
        return ""
    return session.email or session.name or session.subject


def _development(request: Request) -> bool:
    return bool(getattr(request.app.state, "phase", "production") == "development")


def _back(message: str, error: bool = False) -> RedirectResponse:
    key = "error" if error else "status"
    return RedirectResponse(f"{PREFIX}/?{key}={quote(message)}", status_code=303)


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    language = _language(request)
    candidates = _candidates(request)
    services = sorted({candidate.service for candidate in candidates})
    context: dict[str, object] = {
        "base": PREFIX,
        "services": [
            {
                "name": name,
                "containers": [c for c in candidates if c.service == name],
                "updates": [c for c in candidates if c.service == name and c.update_available],
            }
            for name in services
        ],
        "watchtower": [c for c in candidates if c.watchtower],
        "proposals": proposals.all_proposals(request.app.state.generated_dir),
        "development": _development(request),
        "min_why": proposals.MIN_WHY,
        "status_keys": STATUS_KEYS,
        "operation_keys": OPERATION_KEYS,
        "operation_status_keys": OPERATION_STATUS_KEYS,
        "status": request.query_params.get("status"),
        "error": request.query_params.get("error"),
        **language.context(),
    }
    response = templates.TemplateResponse(request=request, name="dock/index.html", context=context)
    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)
    return response


@router.post("/propose", include_in_schema=False, dependencies=[ADMIN_ACTION])
def propose(request: Request, service: str = Form(""), why: str = Form("")) -> Response:
    t = _language(request).t
    changes = [
        proposals.ImageChange(
            container=c.container, image=c.image, from_digest=c.running_digest, to_digest=c.published_digest,
            from_image_id=c.image_id, compose_project=c.compose_project, compose_service=c.compose_service,
            compose_dir=c.compose_dir, compose_files=c.compose_files,
        )
        for c in _candidates(request)
        if c.service == service and c.update_available
    ]
    try:
        proposal = proposals.propose(request.app.state.generated_dir, service, changes, why, _who(request))
    except proposals.ProposalRefused as error:
        return _back(t(error.key, **error.values), error=True)
    return _back(t("dock.status.proposed", id=proposal.id))


@router.post("/validate", include_in_schema=False, dependencies=[ADMIN_ACTION])
def validate(request: Request, proposal: str = Form("")) -> Response:
    t = _language(request).t
    try:
        proposals.validate(
            request.app.state.generated_dir, proposal, _who(request), development=_development(request)
        )
    except proposals.ProposalRefused as error:
        return _back(t(error.key, **error.values), error=True)
    return _back(t("dock.status.validated", id=proposal))


@router.post("/reject", include_in_schema=False, dependencies=[ADMIN_ACTION])
def reject(request: Request, proposal: str = Form(""), reason: str = Form("")) -> Response:
    t = _language(request).t
    try:
        proposals.reject(request.app.state.generated_dir, proposal, _who(request), reason)
    except proposals.ProposalRefused as error:
        return _back(t(error.key, **error.values), error=True)
    return _back(t("dock.status.rejected", id=proposal))
