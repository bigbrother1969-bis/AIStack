"""
Settings' "API keys" section (the owner, 2026-10-09: "dans les
paramètres, il faudrait pouvoir également accéder aux clés API";
every key, the future ones included; write-only, the last four
characters shown). On the local network only, for an administrator.

The keys are declared in `api_keys.yml` (`aistack.api_keys`); a value
entered here is kept in the data directory and laid over the
environment at once, so the web application uses it immediately; the
vigil and the resource-priority monitor take it as `applies` says.
A value is never sent back to the browser.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from aistack import api_keys
from aistack.i18n import Translator
from aistack.renderers.text import escape_text
from aistack.web.authentication import ADMIN_ACTION, current_session
from aistack.web.exposure import LAN_ONLY, arrival_port

router = APIRouter(dependencies=[LAN_ONLY])
SAVE_PATH = "/settings/api-keys"
TEST_PATH = "/settings/api-keys/test"
ANCHOR = "api-keys"

# Literal keys, so the catalog test sees every one of them.
SOURCE_LABELS = {
    api_keys.FROM_SETTINGS: "auth.api_keys.source.settings",
    api_keys.FROM_ENV_FILE: "auth.api_keys.source.env",
    api_keys.ABSENT: "auth.api_keys.source.absent",
}
NOTICES = {
    "saved": "auth.api_keys.notice.saved",
    "cleared": "auth.api_keys.notice.cleared",
    "unknown": "auth.api_keys.notice.unknown",
    "test_ok": "auth.api_keys.notice.test_ok",
    "test_failed": "auth.api_keys.notice.test_failed",
    "test_absent": "auth.api_keys.notice.test_absent",
}

_INPUT = "min-height:32px;padding:0 .5rem;border:1px solid #c6d0dc;border-radius:6px;font-size:.85rem;width:100%;box-sizing:border-box"


def _keys(request: Request) -> list[api_keys.ApiKey]:
    loader: Callable[[], list[api_keys.ApiKey]] = request.app.state.api_keys
    return loader()


def api_keys_section(request: Request, t: Translator) -> str:
    if arrival_port(request) != request.app.state.listeners.lan_port:
        return ""
    session = current_session(request)
    token = escape_text(session.csrf) if session is not None else ""
    generated: Path = request.app.state.generated_dir
    parts = [
        f'<section class="auth-settings" id="{ANCHOR}">',
        f'<h2>{escape_text(t("auth.api_keys.heading"))}</h2>',
        f'<p>{escape_text(t("auth.api_keys.intro"))}</p>',
    ]
    notice = request.query_params.get("api_key", "")
    if notice in NOTICES:
        detail = request.query_params.get("detail", "")
        name = request.query_params.get("name", "")
        failed = notice in ("test_failed", "unknown", "test_absent")
        colour = "#fdecea;border:1px solid #e0a0a0" if failed else "#e8f5e9;border:1px solid #a5d6a7"
        parts.append(
            f'<p role="status" style="padding:.6rem .9rem;border-radius:6px;background:{colour}">'
            f"{escape_text(t(NOTICES[notice], name=name, detail=detail))}</p>"
        )
    parts.append(
        "<table><tr>"
        + "".join(
            f"<th>{escape_text(t(key))}</th>"
            for key in (
                "auth.api_keys.column.key",
                "auth.api_keys.column.state",
                "auth.api_keys.column.change",
            )
        )
        + "</tr>"
    )
    for key in _keys(request):
        source, shown = api_keys.state(key, generated)
        state = escape_text(t(SOURCE_LABELS[source]))
        if shown:
            state += f" <code>{escape_text(shown)}</code>"
        title = escape_text(key.text(key.title, t.lang))
        name = escape_text(key.name)
        kind = "password" if key.secret else "text"
        change = (
            f'<form method="post" action="{SAVE_PATH}" style="margin:0 0 .3rem;display:flex;gap:.4rem">'
            f'<input type="hidden" name="csrf" value="{token}">'
            f'<input type="hidden" name="name" value="{name}">'
            f'<input type="{kind}" name="value" autocomplete="off" style="{_INPUT}" '
            f'placeholder="{escape_text(t("auth.api_keys.placeholder"))}" '
            f'title="{escape_text(t("auth.api_keys.tooltip.value", item=key.text(key.title, t.lang)))}">'
            f'<button type="submit" title="{escape_text(t("auth.api_keys.tooltip.save", item=key.name))}">'
            f'{escape_text(t("auth.api_keys.save"))}</button></form>'
        )
        actions = []
        if source == api_keys.FROM_SETTINGS:
            actions.append(
                f'<form method="post" action="{SAVE_PATH}" style="margin:0;display:inline">'
                f'<input type="hidden" name="csrf" value="{token}">'
                f'<input type="hidden" name="name" value="{name}">'
                f'<input type="hidden" name="clear" value="1">'
                f'<button type="submit" title="{escape_text(t("auth.api_keys.tooltip.clear", item=key.name))}">'
                f'{escape_text(t("auth.api_keys.clear"))}</button></form>'
            )
        if key.test and source != api_keys.ABSENT:
            actions.append(
                f'<form method="post" action="{TEST_PATH}" style="margin:0;display:inline">'
                f'<input type="hidden" name="csrf" value="{token}">'
                f'<input type="hidden" name="name" value="{name}">'
                f'<button type="submit" title="{escape_text(t("auth.api_keys.tooltip.test", item=key.name))}">'
                f'{escape_text(t("auth.api_keys.test"))}</button></form>'
            )
        parts.append(
            "<tr>"
            f'<td><strong>{title}</strong><br><code>{name}</code><br>'
            f'<span style="color:#5b6b7d">{escape_text(key.text(key.used_by, t.lang))} — '
            f'{escape_text(t("auth.api_keys.applies", when=key.text(key.applies, t.lang)))}</span></td>'
            f"<td>{state}</td>"
            f'<td>{change}{" ".join(actions)}</td>'
            "</tr>"
        )
    parts += ["</table>", f'<p class="note">{escape_text(t("auth.api_keys.never_shown"))}</p>', "</section>"]
    return "".join(parts)


def _back(notice: str, name: str = "", detail: str = "") -> RedirectResponse:
    query = f"api_key={notice}&name={quote(name)}"
    if detail:
        query += f"&detail={quote(detail[:200])}"
    return RedirectResponse(f"/settings?{query}#{ANCHOR}", status_code=303)


@router.post(SAVE_PATH, include_in_schema=False, dependencies=[ADMIN_ACTION])
def save(request: Request, name: str = Form(""), value: str = Form(""), clear: str = Form("")) -> Response:
    keys = _keys(request)
    if name not in {key.name for key in keys}:
        return _back("unknown", name)
    generated: Path = request.app.state.generated_dir
    if clear:
        api_keys.write_value(generated, name, None)
        notice = "cleared"
    elif value.strip():
        api_keys.write_value(generated, name, value.strip())
        notice = "saved"
    else:
        return RedirectResponse(f"/settings#{ANCHOR}", status_code=303)
    api_keys.apply_to_environ(generated, keys)
    return _back(notice, name)


@router.post(TEST_PATH, include_in_schema=False, dependencies=[ADMIN_ACTION])
def test(request: Request, name: str = Form("")) -> Response:
    key = next((key for key in _keys(request) if key.name == name), None)
    if key is None or not key.test:
        return _back("unknown", name)
    reason = request.app.state.test_api_key(key.test)
    if reason is None:
        return _back("test_absent", name)
    return _back("test_ok", name) if reason == "" else _back("test_failed", name, reason)


def test_key(kind: str) -> str | None:
    """'' when the key works, the reason when it does not, None when nothing to test with."""

    import os

    if kind == "gemini":
        from aistack.ai_runtime.gemini_engine import GeminiEngine
        from aistack.ai_runtime.yaml import load_ai_runtime_yaml
        from aistack.troubleshooting.guide import AI_RUNTIME

        declared = load_ai_runtime_yaml(AI_RUNTIME).gemini
        if declared is None or not os.environ.get(declared.api_key_env):
            return None
        text, reason = GeminiEngine(declared.model, os.environ[declared.api_key_env], declared.timeout).complete(
            "Reply with the single word OK."
        )
        return "" if text else reason

    if kind == "gotify":
        from aistack.i18n import default_languages, translator_for
        from aistack.vigil import notify

        gotify = notify.Gotify.from_environment()
        if gotify is None:
            return None
        try:
            t = translator_for(default_languages().reference)
            gotify.send(notify.Message("AIStack", t("notify.test"), notify.NORMAL))
        except OSError as error:
            return str(error)
        return ""

    if kind == "syncthing":
        from aistack.sync.declaration import load_sync_declaration
        from aistack.sync.syncthing import SyncthingConfig, SyncthingRefused

        access = load_sync_declaration().syncthing
        if access is None:
            return None
        try:
            SyncthingConfig.of(access).devices()
        except SyncthingRefused as error:
            return str(error)
        return ""

    return None
