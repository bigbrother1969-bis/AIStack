"""
*Selection* — what each content of this host is sent to each device
(`ADR-0012`; generalized by `ADR-0022`, 2026-10-09). LAN only.

    /selection/                         every content × device, its state
    /selection/<content>--<device>/     the content's tree, boxes to tick
    …/save                              records the selection (administrator)
    …/share                             creates the Syncthing folder (administrator)
    …/syncthing-status                  polled by the page

The screen only records: the host executor (`aistack-sync.timer`,
`aistack.cli.sync_apply`) applies. Syncthing is the one host-touching
reader the application injects (`create_app(syncthing=…)`), so a test
replaces it.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.application.yaml import load_application_definition_yaml
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.sync.declaration import SYNCTHING, SyncDeclaration, folder_for, load_sync_declaration, split_pair, target_for
from aistack.sync.screen import definition, page_context, read_applied, record_selection, selection_file, waiting
from aistack.sync.syncthing import SyncthingConfig, SyncthingRefused
from aistack.web.authentication import ADMIN_ACTION, SIGNED_IN_ONLY, current_session
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/selection"
LEGACY_PAIR = "music--phone"

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def _declaration(request: Request) -> SyncDeclaration:
    return load_sync_declaration(request.app.state.paths.sync)


def _pair(request: Request, pair: str) -> tuple[SyncDeclaration, str]:
    declaration = _declaration(request)
    content, destination = split_pair(pair)
    if content not in declaration.contents or destination not in declaration.destinations:
        raise HTTPException(status_code=404)
    if declaration.destinations[destination].kind != SYNCTHING:
        raise HTTPException(status_code=404)
    return declaration, pair


def _legacy(request: Request, pair: str) -> Path | None:
    """The music screen's own selection file, read until the first save here."""

    if pair != LEGACY_PAIR:
        return None
    paths = request.app.state.paths
    try:
        old = load_application_definition_yaml(paths.selection)
    except (OSError, ValueError):
        return None
    return Path(paths.repository_root) / old.selection_file


def _moment(text: str) -> str:
    """An instant as the pages show it: minutes, and the zone said."""

    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return text
    return moment.strftime("%Y-%m-%d %H:%M ") + (moment.tzname() or "")


def _recorded(request: Request, generated: Path, pair: str) -> bool:
    if selection_file(generated, pair).exists():
        return True
    legacy = _legacy(request, pair)
    return legacy is not None and legacy.exists()


def _render(request: Request, name: str, context: dict[str, Any], language: PageLanguage) -> Response:
    context.update(**language.context())
    response = templates.TemplateResponse(request=request, name=name, context=context)
    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)
    return response


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def pairs(request: Request) -> Response:
    language = _language(request)
    declaration = _declaration(request)
    generated = request.app.state.generated_dir
    rows = []
    for destination in declaration.destinations.values():
        if destination.kind != SYNCTHING:
            continue
        entries = []
        for content in declaration.contents.values():
            pair = f"{content.id}--{destination.id}"
            applied = read_applied(generated, pair) or {}
            entries.append(
                {
                    "pair": pair,
                    "content": content.label(language.t.lang),
                    "recorded": _recorded(request, generated, pair),
                    "waiting": waiting(generated, pair),
                    "selected_gb": f"{int(applied.get('selected_bytes') or 0) / 1e9:.1f}",
                    "applied_at": _moment(str(applied.get("at") or "")),
                    "folder": folder_for(declaration, content.id, destination.id),
                }
            )
        rows.append(
            {
                "destination": destination.label(language.t.lang),
                "quota_gb": f"{destination.quota_bytes / 1e9:.0f}" if destination.quota_bytes else "",
                "entries": entries,
            }
        )
    return _render(request, "selection/pairs.html", {"rows": rows, "base": PREFIX, "status": request.query_params.get("status")}, language)


@router.get("/{pair}", response_class=HTMLResponse, include_in_schema=False)
@router.get("/{pair}/", response_class=HTMLResponse, include_in_schema=False)
def pair_page(request: Request, pair: str) -> Response:
    language = _language(request)
    declaration, pair = _pair(request, pair)
    state = request.app.state
    context = page_context(
        declaration, pair, state.kernel, state.generated_dir, state.syncthing, language.t.lang, _legacy(request, pair)
    )
    applied = context["last_generation"]
    if applied is not None:
        report = dict(applied["report"])
        for key in ("linked", "relinked", "removed", "pruned"):
            report[key] = range(int(report.get(key) or 0))
        context["last_generation"] = {"generated_at": _moment(applied["generated_at"]), "report": report}
    context.update(base=f"{PREFIX}/{pair}", status=request.query_params.get("status"), **_folder_state(declaration, pair, language))
    return _render(request, "selection/index.html", context, language)


def _folder_state(declaration: SyncDeclaration, pair: str, language: PageLanguage) -> dict[str, Any]:
    """`share`: the folder to create, when Syncthing answers and does not
    have it; `reshare`: True when it has it, so the offer can be sent
    again."""

    if declaration.syncthing is None:
        return {"share": None, "reshare": False}
    content, destination = split_pair(pair)
    folder = folder_for(declaration, content, destination)
    try:
        if SyncthingConfig.of(declaration.syncthing).folder(folder) is not None:
            return {"share": None, "reshare": True}
    except SyncthingRefused:
        return {"share": None, "reshare": False}
    return {
        "share": {"folder": folder, "device": declaration.destinations[destination].label(language.t.lang)},
        "reshare": False,
    }


@router.get("/{pair}/syncthing-status", include_in_schema=False)
def syncthing_status(request: Request, pair: str) -> dict[str, Any] | None:
    declaration, pair = _pair(request, pair)
    status: dict[str, Any] | None = request.app.state.syncthing(definition(declaration, pair, "fr"))
    return status


@router.post("/{pair}/save", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def save(request: Request, pair: str) -> RedirectResponse:
    declaration, pair = _pair(request, pair)
    form = await request.form()
    session = current_session(request)
    selection = record_selection(
        declaration,
        request.app.state.generated_dir,
        pair,
        [str(value) for value in form.getlist("selected_ids")],
        session.subject if session else "",
    )
    message = _language(request).t("selection.recorded", count=len(selection.selected_ids), pair=pair)
    return RedirectResponse(f"{PREFIX}/{pair}/?status={quote(message)}", status_code=303)


@router.post("/{pair}/share", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def share(request: Request, pair: str) -> RedirectResponse:
    declaration, pair = _pair(request, pair)
    t = _language(request).t
    content, destination = split_pair(pair)
    folder = folder_for(declaration, content, destination)
    access = declaration.syncthing
    if access is None:
        raise HTTPException(status_code=404)
    config = SyncthingConfig.of(access)
    try:
        if config.folder(folder) is None:
            target = target_for(declaration, content, destination)
            label = f"AIStack — {declaration.contents[content].label('fr')} → {destination} ({datetime.now():%Y-%m-%d})"
            config.add_folder(
                folder,
                label,
                access.seen_by_syncthing(target),
                config.device_id(declaration.destinations[destination].device),
            )
        message = t("selection.share.done", folder=folder)
    except SyncthingRefused as error:
        message = t("selection.share.failed", reason=str(error))
    return RedirectResponse(f"{PREFIX}/{pair}/?status={quote(message)}", status_code=303)


@router.post("/{pair}/reshare", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def reshare(request: Request, pair: str) -> RedirectResponse:
    declaration, pair = _pair(request, pair)
    t = _language(request).t
    content, destination = split_pair(pair)
    folder = folder_for(declaration, content, destination)
    if declaration.syncthing is None:
        raise HTTPException(status_code=404)
    config = SyncthingConfig.of(declaration.syncthing)
    try:
        config.reshare(folder, config.device_id(declaration.destinations[destination].device))
        message = t("selection.share.reshared", folder=folder)
    except SyncthingRefused as error:
        message = t("selection.share.failed", reason=str(error))
    return RedirectResponse(f"{PREFIX}/{pair}/?status={quote(message)}", status_code=303)
