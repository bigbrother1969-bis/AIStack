"""
The installation assistant's pages (`ADR-0023` § 5): `/setup/step/<n>`,
one step after the other, each saved from the page.

On the local network only, and only with the installation token
(`aistack.instance.setup_wizard`): `install.sh` shows the address
`/setup/open?token=…`, which leaves the token in a cookie for these
pages alone (`path=/setup`, `SameSite=Strict`) and is then forgotten by
the address bar. Every form also carries a value derived from the
token, so a page from elsewhere cannot post one.

Nobody can sign in yet on a new installation: the token, not a session,
answers for these pages — the way the sign-in forms answer for
themselves.
"""

from __future__ import annotations

import socket
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.config import PACKAGE_ROOT, config_dir, configured, shown_config_dir
from aistack.instance import setup_wizard as wizard
from aistack.instance.first_start import still_shipped
from aistack.renderers.nav import PAGE_NAV_STYLE, render_page_nav
from aistack.web.exposure import LAN_ONLY
from aistack.web.first_start import SETUP_PATH, _language
from aistack.web.templating import templates

router = APIRouter(dependencies=[LAN_ONLY])

OPEN_PATH = "/setup/open"
STEP_PATH = "/setup/step"
COOKIE = wizard.COOKIE

INSTANCE_FILE = "instance_config.yml"
AUTHENTICATION_FILE = "authentication.yml"
SHIPPED_INSTANCE = PACKAGE_ROOT / "instance" / "definitions" / INSTANCE_FILE
SHIPPED_AUTHENTICATION = PACKAGE_ROOT / "authentication" / "definitions" / AUTHENTICATION_FILE

HOST, PUBLIC, SIGN_IN, STORAGE, API_KEYS, CHECK = 1, 2, 3, 4, 5, 6
# Literal keys, so the catalog test sees every one of them.
STEP_TITLES = {
    HOST: "setup.step.host.title",
    PUBLIC: "setup.step.public.title",
    SIGN_IN: "setup.step.sign_in.title",
    STORAGE: "setup.step.storage.title",
    API_KEYS: "setup.step.api_keys.title",
    CHECK: "setup.step.check.title",
}
# The steps the pages hold today; the others are announced.
READY = (HOST, PUBLIC)
ERRORS = {
    "host_name": "setup.error.host_name",
    "port_range": "setup.error.port_range",
    "port_same": "setup.error.port_same",
    "phase": "setup.error.phase",
    "domain": "setup.error.domain",
    "aistack_name": "setup.error.aistack_name",
    "id_name": "setup.error.id_name",
    "names_same": "setup.error.names_same",
    "proxy": "setup.error.proxy",
    "form": "setup.error.form",
    "no_config_dir": "setup.error.no_config_dir",
}


def _now() -> datetime:
    return datetime.now().astimezone()


def _generated(request: Request) -> Path:
    generated: Path = request.app.state.generated_dir
    return generated


def _opened(request: Request) -> str | None:
    """The token, when this browser holds the right one."""

    offered = request.cookies.get(COOKIE)
    if wizard.token_matches(_generated(request), offered):
        return offered
    return None


def _render(request: Request, name: str, context: dict[str, Any], status_code: int = 200) -> Response:
    language = _language(request)
    t = language.t
    response = templates.TemplateResponse(
        request=request,
        name=name,
        status_code=status_code,
        context={
            "page_nav_style": PAGE_NAV_STYLE,
            "page_nav": render_page_nav(t, request.app.state.languages, language.lang),
            "setup_path": SETUP_PATH,
            **context,
            **language.context(),
        },
    )
    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)
    return response


def _closed(request: Request) -> Response:
    return _render(
        request,
        "first_start/wizard_closed.html",
        {"finished": wizard.finished(_generated(request))},
        status_code=403,
    )


@router.get(OPEN_PATH, response_class=HTMLResponse, include_in_schema=False)
def open_assistant(request: Request, token: str = "") -> Response:
    if not wizard.token_matches(_generated(request), token):
        return _closed(request)
    response = RedirectResponse(f"{STEP_PATH}/{_first_unsaved(request)}", status_code=303)
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", path="/setup")
    return response


def _first_unsaved(request: Request) -> int:
    saved = wizard.progress(_generated(request))
    return next((step for step in READY if step not in saved), READY[-1])


@router.get(STEP_PATH, include_in_schema=False)
def resume(request: Request) -> Response:
    if _opened(request) is None:
        return _closed(request)
    return RedirectResponse(f"{STEP_PATH}/{_first_unsaved(request)}", status_code=303)


# --------------------------------------------------------------------
# What each step shows
# --------------------------------------------------------------------


def _current(shipped: Path) -> dict[str, Any]:
    return wizard.read_declaration(configured(shipped))


def _personal(request: Request, step: int, name: str) -> bool:
    """The declaration already holds this installation's values: saved
    here, or never the shipped copy."""

    if step in wizard.progress(_generated(request)):
        return True
    directory = config_dir()
    return directory is not None and (directory / name).is_file() and not still_shipped(directory, name)


def _host_values(request: Request) -> dict[str, str]:
    current = _current(SHIPPED_INSTANCE)
    ports = current.get("service_ports") or {}
    answers = wizard.install_answers(_generated(request))
    personal = _personal(request, HOST, INSTANCE_FILE)
    return {
        "lan_hostname": str(current.get("lan_hostname", ""))
        if personal
        else answers.get("HOST_NAME") or socket.gethostname(),
        "console_port": str(ports.get("console", 8183)),
        "web_lan_port": str(ports.get("web_lan", 8186)),
        "phase": str(current.get("phase", wizard.PRODUCTION)) if personal else wizard.DEVELOPMENT,
    }


def _public_values(request: Request) -> dict[str, str]:
    current = _current(SHIPPED_AUTHENTICATION)
    answers = wizard.install_answers(_generated(request))
    if _personal(request, PUBLIC, AUTHENTICATION_FILE):
        aistack = wizard.clean_name(str(current.get("public_base_url", "")))
        identity = wizard.clean_name(str(current.get("issuer", "")))
        chosen = wizard.choices(_generated(request))
        return {
            "domain": chosen.get("domain") or aistack.partition(".")[2],
            "proxy": chosen.get("proxy", wizard.NGINX_PROXY_MANAGER),
            "aistack_name": aistack,
            "id_name": identity,
        }
    domain = answers.get("DOMAIN", "")
    return {
        "domain": domain,
        "proxy": wizard.NGINX_PROXY_MANAGER,
        "aistack_name": f"aistack.{domain}" if domain else "",
        "id_name": answers.get("ID_NAME") or (f"id.{domain}" if domain else ""),
    }


def _proxy_hosts(request: Request) -> dict[str, Any]:
    """What to create in the reverse proxy, once step 2 is saved."""

    values = _public_values(request)
    host = _host_values(request)
    answers = wizard.install_answers(_generated(request))
    address = answers.get("HOST_ADDRESS") or host["lan_hostname"]
    return {
        "address": address,
        "rows": [
            {"name": values["aistack_name"], "port": host["console_port"], "what": "aistack"},
            {"name": values["id_name"], "port": str(wizard.POCKET_ID_PORT), "what": "pocket_id"},
        ],
        "pocket_id_installed": answers.get("POCKET_ID") == "yes",
        "pocket_id_url": f"https://{values['id_name']}",
        "pocket_id_url_differs": bool(answers.get("ID_NAME")) and answers.get("ID_NAME") != values["id_name"],
    }


def _steps(request: Request, current: int) -> list[dict[str, Any]]:
    saved = wizard.progress(_generated(request))
    return [
        {
            "number": number,
            "title": key,
            "current": number == current,
            "ready": number in READY,
            "saved": saved.get(number, ""),
        }
        for number, key in STEP_TITLES.items()
    ]


def _step_page(
    request: Request,
    step: int,
    token: str,
    *,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    checks: list[wizard.Check] | None = None,
    status_code: int = 200,
) -> Response:
    if values is None:
        values = _host_values(request) if step == HOST else _public_values(request)
    saved = wizard.progress(_generated(request))
    context: dict[str, Any] = {
        "step": step,
        "steps": _steps(request, step),
        "values": values,
        "errors": [ERRORS[error] for error in errors or []],
        "form_token": wizard.form_token(token),
        "action": f"{STEP_PATH}/{step}",
        "saved": step in saved,
        "config_file": _shown(INSTANCE_FILE if step == HOST else AUTHENTICATION_FILE),
        "answers": wizard.install_answers(_generated(request)),
        "checks": checks,
        "next": next((number for number in READY if number > step), None),
    }
    if step == PUBLIC and step in saved:
        context["proxy"] = _proxy_hosts(request)
    return _render(request, "first_start/wizard.html", context, status_code)


def _shown(name: str) -> str:
    directory = shown_config_dir()
    return f"{directory}/{name}" if directory is not None else name


@router.get(f"{STEP_PATH}/{{step}}", response_class=HTMLResponse, include_in_schema=False)
def show_step(request: Request, step: int, check: str = "") -> Response:
    token = _opened(request)
    if token is None:
        return _closed(request)
    if step not in READY:
        return RedirectResponse(f"{STEP_PATH}/{_first_unsaved(request)}", status_code=303)
    checks = None
    if step == PUBLIC and check and PUBLIC in wizard.progress(_generated(request)):
        answer, _errors = wizard.parse_public(**_public_values(request))
        if answer is not None:
            ask: Callable[[str], wizard.Probe] = request.app.state.setup_probe
            checks = [wizard.check_aistack(answer, ask), wizard.check_pocket_id(answer, ask)]
    return _step_page(request, step, token, checks=checks)


@router.post(f"{STEP_PATH}/{{step}}", include_in_schema=False)
async def save_step(request: Request, step: int) -> Response:
    token = _opened(request)
    if token is None:
        return _closed(request)
    form = await request.form()
    values = {name: str(value) for name, value in form.items() if isinstance(value, str)}
    if step not in READY:
        return RedirectResponse(f"{STEP_PATH}/{_first_unsaved(request)}", status_code=303)
    if values.get("form_token", "") != wizard.form_token(token):
        return _step_page(request, step, token, errors=["form"], status_code=403)
    directory = config_dir()
    if directory is None:
        return _step_page(request, step, token, errors=["no_config_dir"], status_code=409)

    when = _now()
    if step == HOST:
        entered = {key: values.get(key, "") for key in ("lan_hostname", "console_port", "web_lan_port", "phase")}
        host, errors = wizard.parse_host(**entered)
        if host is None:
            return _step_page(request, step, token, values=entered, errors=errors, status_code=400)
        data = wizard.host_declaration(_current(SHIPPED_INSTANCE), host)
        wizard.write_declaration(directory, INSTANCE_FILE, data, when)
        wizard.mark_saved(_generated(request), HOST, when)
        return RedirectResponse(f"{STEP_PATH}/{PUBLIC}", status_code=303)

    entered = {key: values.get(key, "") for key in ("domain", "proxy", "aistack_name", "id_name")}
    public, errors = wizard.parse_public(**entered)
    if public is None:
        return _step_page(request, step, token, values=entered, errors=errors, status_code=400)
    data = wizard.public_declaration(_current(SHIPPED_AUTHENTICATION), public)
    wizard.write_declaration(directory, AUTHENTICATION_FILE, data, when)
    wizard.remember(_generated(request), domain=public.domain, proxy=public.proxy)
    wizard.mark_saved(_generated(request), PUBLIC, when)
    return RedirectResponse(f"{STEP_PATH}/{PUBLIC}#proxy-hosts", status_code=303)
