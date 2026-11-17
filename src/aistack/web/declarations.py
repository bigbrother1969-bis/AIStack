"""Settings' "Shipped declarations" section (administrators, container only).

Shows which shipped declarations changed since the owner's copy, with the
diff, and lets the owner mark one as seen. The rules live in
`aistack.instance.declarations`.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from aistack.config import config_dir, shipped_definitions, shown_config_dir
from aistack.i18n import Translator
from aistack.declaration import observe, validate
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


def hand_edits_section(request: Request, t: Translator) -> str:
    """
    Settings' "Declarations edited by hand": what the files of the configuration
    directory hold that their loader does not read (now), and the edits made by
    hand with their difference (ADR-0027 § 12). Read only.
    """

    directory = config_dir()
    if directory is None:
        return ""
    generated = request.app.state.generated_dir
    parts = [
        '<section class="auth-settings" id="hand-edits">',
        f'<h2>{escape_text(t("auth.hand_edits.heading"))}</h2>',
        f'<p>{escape_text(t("auth.hand_edits.intro"))}</p>',
    ]
    invalid = validate.validate(directory, generated, shipped_definitions())
    if invalid:
        parts.append(f'<h3>{escape_text(t("auth.hand_edits.invalid"))}</h3>')
    for item in invalid:
        kept = validate.last_valid_copy(generated, item.name, observe.seen_path(generated, item.name).parent)
        parts.append(
            f'<p style="padding:.6rem .9rem;border-radius:6px;background:#fdecea;border:1px solid #f5c6cb">'
            f'<code>{escape_text(item.name)}</code> — {escape_text(item.error)}<br>'
            f'{escape_text(t("auth.hand_edits.last_valid"))} '
            f'<code>{escape_text(kept) if kept else escape_text(t("auth.hand_edits.no_copy"))}</code></p>'
        )
    edits = observe.hand_edits(generated)
    if not edits:
        parts.append(f'<p>{escape_text(t("auth.hand_edits.none"))}</p>')
    for edit in edits:
        state = t("auth.hand_edits.valid") if edit.valid else t("auth.hand_edits.not_read", error=edit.error)
        parts.append(
            f'<h3><code>{escape_text(edit.name)}</code> <small>{escape_text(edit.at)}</small></h3>'
            f'<p>{escape_text(state)}</p>'
        )
        parts.append(
            f'<pre style="{_PRE}">{escape_text(chr(10).join(edit.diff)) or escape_text(t("auth.hand_edits.no_diff"))}</pre>'
        )
        if edit.cut:
            parts.append(
                f'<p class="note">{escape_text(t("auth.declarations.cut", count=observe.MAX_DIFF_LINES))}</p>'
            )
    parts.append("</section>")
    return "".join(parts)
