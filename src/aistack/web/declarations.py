"""
Settings' "Shipped declarations" section, for an administrator, in the
container only (`ADR-0017` open point, decided by the owner 2026-10-05):
which shipped declarations changed since the owner's copy, with the
difference, and a way to say "seen, I keep mine". The rules are
`aistack.instance.declarations`'.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from aistack.config import config_dir, shipped_definitions, shown_config_dir
from aistack.i18n import Translator
from aistack.instance import declarations
from aistack.renderers.text import escape_text
from aistack.web.authentication import ADMIN_ACTION, current_session
from aistack.web.exposure import PUBLIC

router = APIRouter(dependencies=[PUBLIC])
SEEN_PATH = "/settings/declarations/seen"
ANCHOR = "declarations"

_PRE = (
    "white-space:pre-wrap;word-break:break-all;background:#f4f6f9;"
    "border:1px solid #dde4ed;border-radius:6px;padding:.6rem .8rem;font-size:.85rem"
)


def declarations_section(request: Request, t: Translator) -> str:
    directory = config_dir()
    if directory is None:
        return ""
    shown = shown_config_dir() or str(directory)
    session = current_session(request)
    token = escape_text(session.csrf) if session is not None else ""
    parts = [
        f'<section class="auth-settings" id="{ANCHOR}">',
        f'<h2>{escape_text(t("auth.declarations.heading"))}</h2>',
        f'<p>{escape_text(t("auth.declarations.intro", directory=shown))}</p>',
    ]
    marked = request.query_params.get("declaration", "")
    if marked:
        parts.append(
            '<p style="padding:.6rem .9rem;border-radius:6px;background:#e8f5e9;border:1px solid #a5d6a7">'
            f'{escape_text(t("auth.declarations.marked", name=marked))}</p>'
        )
    found = declarations.divergences(directory, shipped_definitions())
    if not found:
        parts.append(f'<p>{escape_text(t("auth.declarations.none"))}</p>')
    for divergence in found:
        name = escape_text(divergence.name)
        parts.append(f'<h3><code>{name}</code></h3>')
        parts.append(f'<p>{escape_text(t("auth.declarations.changed", name=divergence.name))}</p>')
        parts.append(f'<pre style="{_PRE}">{escape_text(chr(10).join(divergence.diff))}</pre>')
        if divergence.cut:
            parts.append(
                f'<p class="note">{escape_text(t("auth.declarations.cut", count=declarations.MAX_DIFF_LINES))}</p>'
            )
        parts.append(f'<p>{escape_text(t("auth.declarations.adopt"))}</p>')
        # The image keeps the source it was built from under /app/src.
        command = f"docker compose cp web:/app/src/{divergence.shipped} ./config/{divergence.name}"
        parts.append(f'<pre style="{_PRE}">{escape_text(command)}</pre>')
        parts.append(
            f'<form method="post" action="{SEEN_PATH}">'
            f'<input type="hidden" name="csrf" value="{token}">'
            f'<input type="hidden" name="name" value="{name}">'
            f'<button type="submit" title="{escape_text(t("auth.declarations.tooltip.seen"))}">'
            f'{escape_text(t("auth.declarations.seen"))}</button></form>'
        )
    parts.append("</section>")
    return "".join(parts)


@router.post(SEEN_PATH, include_in_schema=False, dependencies=[ADMIN_ACTION])
def mark_seen(request: Request, name: str = Form("")) -> Response:
    directory = config_dir()
    if directory is None or not declarations.mark_seen(directory, shipped_definitions(), name):
        return RedirectResponse(f"/settings#{ANCHOR}", status_code=303)
    return RedirectResponse(f"/settings?declaration={quote(name)}#{ANCHOR}", status_code=303)
