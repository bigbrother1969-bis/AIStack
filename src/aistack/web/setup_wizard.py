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

import os
import socket
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from urllib.parse import quote

from aistack import api_keys
from aistack.authentication.definition import AuthenticationDefinition, load_authentication_yaml
from aistack.authentication.local_admin import hash_password
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
READY = (HOST, PUBLIC, SIGN_IN, STORAGE, API_KEYS, CHECK)
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
    "sign_in_mode": "setup.error.sign_in_mode",
    "client_id": "setup.error.client_id",
    "client_secret": "setup.error.client_secret",
    "password_short": "setup.error.password_short",
    "password_differs": "setup.error.password_differs",
    "password_required": "setup.error.password_required",
    "folder_invalid": "setup.error.folder_invalid",
    "folder_refused": "setup.error.folder_refused",
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


def _definition() -> AuthenticationDefinition:
    return load_authentication_yaml(configured(SHIPPED_AUTHENTICATION))


def _present(stored: dict[str, str], name: str) -> str:
    return stored.get(name) or os.environ.get(name, "").strip()


def _sign_in_values(request: Request) -> dict[str, str]:
    definition = _definition()
    stored = wizard.sign_in_values(_generated(request))
    chosen = wizard.choices(_generated(request)).get("sign_in")
    client_id = _present(stored, definition.client_id_env)
    pocket_id = client_id or wizard.install_answers(_generated(request)).get("POCKET_ID") == "yes"
    return {
        "mode": chosen or (wizard.POCKET_ID if pocket_id else wizard.LOCAL_ONLY),
        "client_id": client_id,
    }


def _sign_in_view(request: Request) -> dict[str, Any]:
    """What step 3 says around its form: never a secret, only whether
    there is one and its last four characters."""

    definition = _definition()
    stored = wizard.sign_in_values(_generated(request))
    secret = _present(stored, definition.client_secret_env)
    host = _host_values(request)
    lan = f"http://{host['lan_hostname']}:{host['web_lan_port']}"
    public = definition.public_base_url
    return {
        "secret_shown": ("…" + secret[-4:]) if len(secret) > 8 else ("…" if secret else ""),
        "has_admin": bool(_present(stored, definition.local_admin_env)),
        "admin_group": definition.admin_group,
        "pocket_id": definition.issuer,
        "callbacks": [definition.redirect_uri_for(public), definition.redirect_uri_for(lan)],
        "logouts": [definition.after_logout_uri_for(public), definition.after_logout_uri_for(lan)],
        "lan": lan,
    }


def _storage_values(request: Request) -> dict[str, Any]:
    return {"folders": wizard.read_volumes(config_dir()), "typed": ""}


def _size(value: int) -> str:
    size = float(value)
    for unit in ("o", "Kio", "Mio", "Gio", "Tio"):
        if size < 1024 or unit == "Tio":
            return f"{size:.0f} {unit}" if unit == "o" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} Tio"


def _storage_view(request: Request, values: dict[str, Any]) -> dict[str, Any]:
    from aistack.host.mounts import usage

    generated = _generated(request)
    measured = usage(str(generated))
    chosen = list(values.get("folders") or [])
    mounts = [
        {"point": mount.point, "device": mount.device, "type": mount.fstype, "checked": mount.point in chosen}
        for mount in wizard.offered_mounts(generated)
    ]
    shown = {mount["point"] for mount in mounts}
    install_dir = wizard.install_answers(generated).get("INSTALL_DIR") or "/srv/aistack"
    return {
        "data_dir": os.environ.get("AISTACK_DATA_DIR", "./data"),
        "data_free": _size(measured.free) if measured is not None else "",
        "data_total": _size(measured.total) if measured is not None else "",
        "always": wizard.ALWAYS_READ,
        "mounts": mounts,
        "known_mounts": bool(wizard.host_mounts(generated)),
        "typed": values.get("typed") or "\n".join(path for path in chosen if path not in shown),
        "install_dir": install_dir,
        "compose_file": f"COMPOSE_FILE=docker-compose.yml:config/{wizard.VOLUMES_FILE}",
    }


# Literal keys, so the catalog test sees every one of them.
KEY_SOURCES = {
    api_keys.FROM_SETTINGS: "setup.step.api_keys.source.settings",
    api_keys.FROM_ENV_FILE: "setup.step.api_keys.source.env",
    api_keys.ABSENT: "setup.step.api_keys.source.absent",
}
KEY_NOTICES = {
    "saved": "setup.step.api_keys.notice.saved",
    "cleared": "setup.step.api_keys.notice.cleared",
    "test_ok": "setup.step.api_keys.notice.test_ok",
    "test_failed": "setup.step.api_keys.notice.test_failed",
    "test_absent": "setup.step.api_keys.notice.test_absent",
}


def _keys_view(request: Request) -> list[dict[str, Any]]:
    """Every key of `api_keys.yml`, with its procedure: never a value,
    only where it comes from and the last four characters."""

    generated = _generated(request)
    t = _language(request).t
    answers = wizard.install_answers(generated)
    host = answers.get("HOST_ADDRESS") or _host_values(request)["lan_hostname"]
    loader: Callable[[], list[api_keys.ApiKey]] = request.app.state.api_keys
    shown_notice = request.query_params.get("key", "")
    notice = request.query_params.get("notice", "")
    view = []
    for key in loader():
        source, shown = api_keys.state(key, generated)
        prerequisite_missing = bool(key.prerequisite) and answers.get(key.prerequisite.upper().replace("-", "_")) == "no"
        view.append(
            {
                "name": key.name,
                "title": key.text(key.title, t.lang),
                "used_by": key.text(key.used_by, t.lang),
                "applies": key.text(key.applies, t.lang),
                "secret": key.secret,
                "source": t(KEY_SOURCES[source]),
                "present": source != api_keys.ABSENT,
                "from_assistant": source == api_keys.FROM_SETTINGS,
                "shown": shown,
                "steps": key.steps(t.lang, host),
                "suggested": key.suggested.replace("{host}", host) if source == api_keys.ABSENT else "",
                "test": bool(key.test),
                "prerequisite_missing": prerequisite_missing,
                "notice": t(
                    KEY_NOTICES[notice], name=key.name, detail=request.query_params.get("detail", "")
                )
                if shown_notice == key.name and notice in KEY_NOTICES
                else "",
                "notice_failed": notice in ("test_failed", "test_absent"),
            }
        )
    return view


def _api_keys_values(request: Request) -> dict[str, Any]:
    return {}


# Literal keys, so the catalog test sees every one of them.
PREREQUISITES = {
    "pocket_id": ("setup.step.check.item.pocket_id", "setup.step.check.lost.pocket_id"),
    "ollama": ("setup.step.check.item.ollama", "setup.step.check.lost.ollama"),
    "gemini": ("setup.step.check.item.gemini", "setup.step.check.lost.gemini"),
    "gotify": ("setup.step.check.item.gotify", "setup.step.check.lost.gotify"),
    "syncthing": ("setup.step.check.item.syncthing", "setup.step.check.lost.syncthing"),
}
OK, FAILED, ABSENT = "ok", "failed", "absent"


def _run_checks(request: Request) -> list[dict[str, str]]:
    """Each prerequisite asked once (ADR-0023 § 5.6). Gotify's test sends
    a message to the phone: it runs on the owner's click only."""

    from aistack.ai_runtime.yaml import load_ai_runtime_yaml
    from aistack.troubleshooting.guide import AI_RUNTIME

    generated = _generated(request)
    t = _language(request).t
    results: list[tuple[str, str, str]] = []
    if wizard.oidc_wanted(generated):
        answer, _errors = wizard.parse_public(**_public_values(request))
        if answer is None:
            results.append(("pocket_id", ABSENT, ""))
        else:
            found = wizard.check_pocket_id(answer, _ask(request))
            results.append(("pocket_id", OK if found.ok else FAILED, found.detail if not found.ok else found.url))
    runtime = load_ai_runtime_yaml(AI_RUNTIME)
    if runtime.model:
        ollama = wizard.check_ollama(runtime.host, runtime.port, runtime.model, _ask(request))
        results.append(("ollama", OK if ollama.ok else FAILED, ollama.detail))
    else:
        results.append(("ollama", ABSENT, ""))
    tester: Callable[[str], str | None] = request.app.state.test_api_key
    for kind in ("gemini", "gotify", "syncthing"):
        reason = tester(kind)
        results.append((kind, ABSENT if reason is None else OK if reason == "" else FAILED, reason or ""))
    return [
        {"name": t(PREREQUISITES[kind][0]), "state": state, "detail": detail, "lost": t(PREREQUISITES[kind][1])}
        for kind, state, detail in results
    ]


def _check_view(request: Request) -> dict[str, Any]:
    generated = _generated(request)
    install_dir = wizard.install_answers(generated).get("INSTALL_DIR") or "/srv/aistack"
    return {
        "missing": [STEP_TITLES[step] for step in wizard.missing_steps(generated)],
        "install_dir": install_dir,
    }


VALUES = {
    CHECK: lambda request: {},
    HOST: _host_values,
    PUBLIC: _public_values,
    SIGN_IN: _sign_in_values,
    STORAGE: _storage_values,
    API_KEYS: _api_keys_values,
}
FILES = {HOST: INSTANCE_FILE, PUBLIC: AUTHENTICATION_FILE, STORAGE: wizard.VOLUMES_FILE}


def _step_page(
    request: Request,
    step: int,
    token: str,
    *,
    values: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    checks: list[Any] | None = None,
    status_code: int = 200,
) -> Response:
    if values is None:
        values = VALUES[step](request)
    saved = wizard.progress(_generated(request))
    following = next((number for number in READY if number > step), None)
    context: dict[str, Any] = {
        "step": step,
        "steps": _steps(request, step),
        "values": values,
        "errors": [ERRORS[error] for error in errors or []],
        "form_token": wizard.form_token(token),
        "action": f"{STEP_PATH}/{step}",
        "saved": step in saved,
        "config_file": _shown(FILES[step]) if step in FILES else "",
        "answers": wizard.install_answers(_generated(request)),
        "checks": checks,
        "next": following,
        "next_title": STEP_TITLES[following] if following is not None else "",
    }
    if step == PUBLIC and step in saved:
        context["proxy"] = _proxy_hosts(request)
    if step == SIGN_IN:
        context["sign_in"] = _sign_in_view(request)
    if step == STORAGE:
        context["storage"] = _storage_view(request, values)
    if step == API_KEYS:
        context["keys"] = _keys_view(request)
    if step == CHECK:
        context["final"] = _check_view(request)
    return _render(request, "first_start/wizard.html", context, status_code)


def _shown(name: str) -> str:
    directory = shown_config_dir()
    return f"{directory}/{name}" if directory is not None else name


def _ask(request: Request) -> Callable[[str], wizard.Probe]:
    ask: Callable[[str], wizard.Probe] = request.app.state.setup_probe
    return ask


@router.get(f"{STEP_PATH}/{{step}}", response_class=HTMLResponse, include_in_schema=False)
def show_step(request: Request, step: int, check: str = "") -> Response:
    token = _opened(request)
    if token is None:
        return _closed(request)
    if step not in READY:
        return RedirectResponse(f"{STEP_PATH}/{_first_unsaved(request)}", status_code=303)
    if step == CHECK:
        return _step_page(request, step, token, checks=_run_checks(request) if check else None)
    checks = None
    if check and step in (PUBLIC, SIGN_IN) and step in wizard.progress(_generated(request)):
        answer, _errors = wizard.parse_public(**_public_values(request))
        if answer is not None:
            checks = [wizard.check_aistack(answer, _ask(request))] if step == PUBLIC else []
            checks.append(wizard.check_pocket_id(answer, _ask(request)))
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
    generated = _generated(request)
    if step == HOST:
        entered = {key: values.get(key, "") for key in ("lan_hostname", "console_port", "web_lan_port", "phase")}
        host, errors = wizard.parse_host(**entered)
        if host is None:
            return _step_page(request, step, token, values=entered, errors=errors, status_code=400)
        data = wizard.host_declaration(_current(SHIPPED_INSTANCE), host)
        wizard.write_declaration(directory, INSTANCE_FILE, data, when)
        wizard.mark_saved(generated, HOST, when)
        return RedirectResponse(f"{STEP_PATH}/{PUBLIC}", status_code=303)

    if step == PUBLIC:
        entered = {key: values.get(key, "") for key in ("domain", "proxy", "aistack_name", "id_name")}
        public, errors = wizard.parse_public(**entered)
        if public is None:
            return _step_page(request, step, token, values=entered, errors=errors, status_code=400)
        data = wizard.public_declaration(_current(SHIPPED_AUTHENTICATION), public)
        wizard.write_declaration(directory, AUTHENTICATION_FILE, data, when)
        wizard.remember(generated, domain=public.domain, proxy=public.proxy)
        wizard.mark_saved(generated, PUBLIC, when)
        return RedirectResponse(f"{STEP_PATH}/{PUBLIC}#proxy-hosts", status_code=303)

    if step == API_KEYS:
        return _save_key(request, values, when)

    if step == CHECK:
        if wizard.missing_steps(generated):
            return RedirectResponse(f"{STEP_PATH}/{CHECK}", status_code=303)
        wizard.mark_saved(generated, CHECK, when)
        wizard.finish(generated, when)
        response = _render(request, "first_start/wizard_finished.html", _check_view(request) | _finished_view(request))
        response.delete_cookie(COOKIE, path="/setup")
        return response

    if step == STORAGE:
        typed = values.get("typed", "")
        folders, errors = wizard.parse_folders([str(item) for item in form.getlist("folder")], typed)
        if errors:
            return _step_page(
                request, step, token, values={"folders": folders, "typed": typed}, errors=errors, status_code=400
            )
        wizard.write_volumes(directory, folders, when)
        wizard.mark_saved(generated, STORAGE, when)
        return RedirectResponse(f"{STEP_PATH}/{STORAGE}#saved", status_code=303)

    # SIGN_IN — the passwords are never sent back to the page, even refused.
    definition = _definition()
    stored = wizard.sign_in_values(generated)
    mode, client_id = values.get("mode", ""), values.get("client_id", "")
    answer, errors = wizard.parse_sign_in(
        mode,
        client_id,
        values.get("client_secret", ""),
        values.get("password", ""),
        values.get("again", ""),
        has_client_secret=bool(_present(stored, definition.client_secret_env)),
        has_admin=bool(_present(stored, definition.local_admin_env)),
    )
    if answer is None:
        return _step_page(
            request, step, token, values={"mode": mode, "client_id": client_id}, errors=errors, status_code=400
        )
    if answer.client_id is not None:
        wizard.keep_sign_in(generated, definition.client_id_env, answer.client_id)
    if answer.client_secret is not None:
        wizard.keep_sign_in(generated, definition.client_secret_env, answer.client_secret)
    if answer.admin_password:
        wizard.keep_sign_in(generated, definition.local_admin_env, hash_password(answer.admin_password))
    wizard.remember(generated, sign_in=answer.mode)
    wizard.mark_saved(generated, SIGN_IN, when)
    return RedirectResponse(f"{STEP_PATH}/{SIGN_IN}#saved", status_code=303)


def _save_key(request: Request, values: dict[str, str], when: datetime) -> Response:
    """One key saved, cleared or tested — as in Settings, same store —
    or the step marked done."""

    generated = _generated(request)
    action = values.get("action", "save")
    if action == "done":
        wizard.mark_saved(generated, API_KEYS, when)
        following = next((number for number in READY if number > API_KEYS), API_KEYS)
        return RedirectResponse(f"{STEP_PATH}/{following}", status_code=303)
    keys: list[api_keys.ApiKey] = request.app.state.api_keys()
    key = next((key for key in keys if key.name == values.get("name", "")), None)
    if key is None:
        return RedirectResponse(f"{STEP_PATH}/{API_KEYS}", status_code=303)

    def back(notice: str, detail: str = "") -> RedirectResponse:
        query = f"key={quote(key.name)}&notice={notice}"
        if detail:
            query += f"&detail={quote(detail[:200])}"
        return RedirectResponse(f"{STEP_PATH}/{API_KEYS}?{query}#key-{key.name}", status_code=303)

    if action == "test":
        reason = request.app.state.test_api_key(key.test) if key.test else None
        if reason is None:
            return back("test_absent")
        return back("test_ok") if reason == "" else back("test_failed", reason)
    if action == "clear":
        api_keys.write_value(generated, key.name, None)
        notice = "cleared"
    elif values.get("value", "").strip():
        api_keys.write_value(generated, key.name, values["value"].strip())
        notice = "saved"
    else:
        return back("")
    api_keys.apply_to_environ(generated, keys)
    return back(notice)


def _finished_view(request: Request) -> dict[str, Any]:
    definition = _definition()
    host = _host_values(request)
    return {
        "public": definition.public_base_url,
        "lan": f"http://{host['lan_hostname']}:{host['web_lan_port']}",
        "oidc": wizard.oidc_wanted(_generated(request)),
    }
