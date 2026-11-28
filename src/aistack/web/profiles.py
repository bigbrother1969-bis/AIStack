"""Settings' "Profiles" section, for administrators (`ADR-0034`, GP2).

Lists every account AIStack has an opinion about — pre-assigned or
already seen — lets an administrator change a profile or revoke one
(cutting any live session of theirs at once,
`aistack.web.authentication.revoke_account`), pre-assign a profile to
an identifier before its first sign-in, and shows the change journal.
Thin: every decision (priority order, immediate revocation) was made
at GP1 in `aistack.authentication.profiles` and
`aistack.web.authentication`; this module only renders and dispatches.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from aistack.authentication.profiles import ADMIN, REVOKED, USER
from aistack.i18n import Translator
from aistack.renderers.text import escape_text
from aistack.web.authentication import (
    ADMIN_ACTION,
    Authentication,
    current_session,
    assign_account,
    revoke_account,
)
from aistack.web.exposure import PUBLIC

router = APIRouter(dependencies=[PUBLIC])
ASSIGN_PATH = "/settings/profiles/assign"
REVOKE_PATH = "/settings/profiles/revoke"
ANCHOR = "profiles"

# Literal keys, so the catalog test sees every one of them.
NOTICES = {
    "assigned": "auth.profiles.notice.assigned",
    "revoked": "auth.profiles.notice.revoked",
    "empty": "auth.profiles.notice.empty",
}
_PROFILE_LABELS = {ADMIN: "auth.profile.admin", USER: "auth.profile.user"}

_INPUT = "min-height:32px;padding:0 .5rem;border:1px solid #c6d0dc;border-radius:6px;font-size:.85rem;min-width:14rem;box-sizing:border-box"
_SELECT = "min-height:32px;padding:0 .3rem;border:1px solid #c6d0dc;border-radius:6px;font-size:.85rem"


def _authentication(request: Request) -> Authentication:
    return request.app.state.authentication


def _when(at: float) -> str:
    import time

    return time.strftime("%Y-%m-%d %H:%M", time.localtime(at))


def _profile_label(t: Translator, profile: str) -> str:
    if profile == REVOKED:
        return escape_text(t("auth.profiles.status.revoked"))
    return escape_text(t(_PROFILE_LABELS.get(profile, "auth.profile.user")))


def _options(t: Translator, selected: str) -> str:
    return "".join(
        f'<option value="{profile}"{" selected" if profile == selected else ""}>'
        f"{escape_text(t(label))}</option>"
        for profile, label in _PROFILE_LABELS.items()
    )


def profiles_section(request: Request, t: Translator) -> str:
    authentication = _authentication(request)
    session = current_session(request)
    token = escape_text(session.csrf) if session is not None else ""

    parts = [
        f'<section class="auth-settings" id="{ANCHOR}">',
        f'<h2>{escape_text(t("auth.profiles.heading"))}</h2>',
        f'<p>{escape_text(t("auth.profiles.intro"))}</p>',
    ]

    notice = request.query_params.get("profile", "")
    if notice in NOTICES:
        identifier = request.query_params.get("identifier", "")
        failed = notice == "empty"
        colour = "#fdecea;border:1px solid #e0a0a0" if failed else "#e8f5e9;border:1px solid #a5d6a7"
        parts.append(
            f'<p role="status" style="padding:.6rem .9rem;border-radius:6px;background:{colour}">'
            f"{escape_text(t(NOTICES[notice], identifier=identifier))}</p>"
        )

    accounts = authentication.profiles.known() if authentication.profiles is not None else []

    parts.append(
        "<table><tr>"
        + "".join(
            f"<th>{escape_text(t(key))}</th>"
            for key in (
                "auth.profiles.column.identifier",
                "auth.profiles.column.profile",
                "auth.profiles.column.assigned",
                "auth.profiles.column.change",
            )
        )
        + "</tr>"
    )
    for account in accounts:
        change_form = (
            f'<form method="post" action="{ASSIGN_PATH}" style="margin:0 0 .3rem;display:flex;gap:.3rem">'
            f'<input type="hidden" name="csrf" value="{token}">'
            f'<input type="hidden" name="identifier" value="{escape_text(account.identifier)}">'
            f'<select name="profile" style="{_SELECT}">{_options(t, account.profile)}</select>'
            f'<button type="submit" title="{escape_text(t("auth.profiles.tooltip.change", item=account.identifier))}">'
            f'{escape_text(t("auth.profiles.change"))}</button></form>'
        )
        revoke_form = (
            f'<form method="post" action="{REVOKE_PATH}" style="margin:0;display:inline">'
            f'<input type="hidden" name="csrf" value="{token}">'
            f'<input type="hidden" name="identifier" value="{escape_text(account.identifier)}">'
            f'<button type="submit" title="{escape_text(t("auth.profiles.tooltip.revoke", item=account.identifier))}">'
            f'{escape_text(t("auth.profiles.revoke"))}</button></form>'
        )
        parts.append(
            "<tr>"
            f"<td><code>{escape_text(account.identifier)}</code></td>"
            f"<td>{_profile_label(t, account.profile)}</td>"
            f"<td>{escape_text(_when(account.assigned_at))}</td>"
            f"<td>{change_form}{revoke_form}</td>"
            "</tr>"
        )
    parts.append("</table>")
    if not accounts:
        parts.append(f'<p>{escape_text(t("auth.profiles.empty"))}</p>')

    parts += [
        f'<h3>{escape_text(t("auth.profiles.assign_heading"))}</h3>',
        f'<form method="post" action="{ASSIGN_PATH}" style="display:flex;gap:.4rem;align-items:center;flex-wrap:wrap">',
        f'<input type="hidden" name="csrf" value="{token}">',
        f'<input type="text" name="identifier" autocomplete="off" style="{_INPUT}" '
        f'placeholder="{escape_text(t("auth.profiles.placeholder.identifier"))}" '
        f'title="{escape_text(t("auth.profiles.tooltip.identifier"))}">',
        f'<select name="profile" style="{_SELECT}">{_options(t, ADMIN)}</select>',
        f'<button type="submit" title="{escape_text(t("auth.profiles.tooltip.assign"))}">'
        f'{escape_text(t("auth.profiles.assign"))}</button>',
        "</form>",
    ]

    parts.append(f'<h3>{escape_text(t("auth.profiles.journal_heading"))}</h3>')
    changes = authentication.profiles.changes() if authentication.profiles is not None else []
    if not changes:
        parts.append(f'<p>{escape_text(t("auth.profiles.journal_empty"))}</p>')
    else:
        parts += [
            "<table><tr>"
            + "".join(
                f"<th>{escape_text(t(key))}</th>"
                for key in (
                    "auth.profiles.column.when",
                    "auth.profiles.column.identifier",
                    "auth.profiles.column.profile",
                    "auth.profiles.column.by",
                )
            )
            + "</tr>"
        ]
        for change in changes:
            parts.append(
                "<tr>"
                f"<td>{escape_text(_when(change.at))}</td>"
                f"<td><code>{escape_text(change.identifier)}</code></td>"
                f"<td>{_profile_label(t, change.profile)}</td>"
                f"<td>{escape_text(change.by or '—')}</td>"
                "</tr>"
            )
        parts.append("</table>")

    parts.append("</section>")
    return "".join(parts)


def _back(notice: str, identifier: str = "") -> RedirectResponse:
    query = f"profile={notice}&identifier={quote(identifier)}"
    return RedirectResponse(f"/settings?{query}#{ANCHOR}", status_code=303)


@router.post(ASSIGN_PATH, include_in_schema=False, dependencies=[ADMIN_ACTION])
def assign(request: Request, identifier: str = Form(""), profile: str = Form("")) -> Response:
    identifier = identifier.strip()
    if not identifier or profile not in (ADMIN, USER):
        return _back("empty", identifier)
    session = current_session(request)
    by = (session.name or session.subject) if session is not None else ""
    assign_account(_authentication(request), identifier, profile, by)
    return _back("assigned", identifier)


@router.post(REVOKE_PATH, include_in_schema=False, dependencies=[ADMIN_ACTION])
def revoke(request: Request, identifier: str = Form("")) -> Response:
    identifier = identifier.strip()
    if not identifier:
        return _back("empty", identifier)
    session = current_session(request)
    by = (session.name or session.subject) if session is not None else ""
    revoke_account(_authentication(request), identifier, by)
    return _back("revoked", identifier)
