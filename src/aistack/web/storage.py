"""
Settings' "Disks and mounts" section, for an administrator (asked by
the owner, 2026-10-04): every real mount the host sees, its size, free
space and access, and which of AIStack's own components lives on it.

Below it, where AIStack's data lives (1.8, decided by the owner
2026-10-04): `reports/generated` as one block, a directory to move it
to, and — once chosen — the commands that move it. AIStack records the
choice and never moves anything itself (`aistack.instance.data_location`).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from aistack.config import config_dir
from aistack.host.mounts import MountRow, disks_and_mounts
from aistack.i18n import Translator
from aistack.instance import data_location
from aistack.renderers.text import escape_text
from aistack.web.authentication import ADMIN_ACTION, current_session
from aistack.web.exposure import PUBLIC

router = APIRouter(dependencies=[PUBLIC])
LOCATION_PATH = "/settings/storage/location"
LOCATION_ANCHOR = "data-location"

# Literal keys, so the catalog test sees every one of them.
LOCATION_NOTICES = {
    "saved": "auth.storage.location.saved",
    "cleared": "auth.storage.location.cleared",
    "relative": "auth.storage.location.refused.relative",
    "missing": "auth.storage.location.refused.missing",
    "same": "auth.storage.location.refused.same",
    "inside": "auth.storage.location.refused.inside",
    "space": "auth.storage.location.refused.space",
}
STATE_LABELS = {
    data_location.NONE: "auth.storage.location.state.none",
    data_location.PLANNED: "auth.storage.location.state.planned",
    data_location.DONE: "auth.storage.location.state.done",
}

REPO_ROOT = Path(__file__).resolve().parents[3]

# Literal keys, so the catalog test sees every one of them.
COMPONENT_LABELS = {
    "code": "auth.storage.component.code",
    "generated": "auth.storage.component.generated",
    "graph": "auth.storage.component.graph",
    "explications": "auth.storage.component.explications",
    "sessions": "auth.storage.component.sessions",
}


def components(generated_dir: Path) -> dict[str, Path]:
    """What AIStack keeps, and where (label key → path)."""

    return {
        "code": REPO_ROOT,
        "generated": generated_dir,
        "graph": generated_dir / "timemachine" / "graph",
        "explications": generated_dir / "explications",
        "sessions": generated_dir / "web" / "sessions.sqlite3",
    }


def live_storage(generated_dir: Path) -> list[MountRow]:
    return disks_and_mounts(components(generated_dir))


def _size(value: int) -> str:
    size = float(value)
    for unit in ("o", "Kio", "Mio", "Gio", "Tio"):
        if size < 1024 or unit == "Tio":
            return f"{size:.0f} {unit}" if unit == "o" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} Tio"


def storage_section(request: Request, t: Translator) -> str:
    rows: list[MountRow] = request.app.state.storage(request.app.state.generated_dir)

    head = "".join(
        f"<th>{escape_text(t(key))}</th>"
        for key in (
            "auth.storage.column.point",
            "auth.storage.column.device",
            "auth.storage.column.type",
            "auth.storage.column.size",
            "auth.storage.column.free",
            "auth.storage.column.access",
            "auth.storage.column.aistack",
        )
    )
    lines = []
    for row in rows:
        if row.usage is None:
            size = free = escape_text(t("auth.storage.not_answering"))
        else:
            size = escape_text(_size(row.usage.total))
            percent = 100 * row.usage.free / row.usage.total if row.usage.total else 0
            free = escape_text(f"{_size(row.usage.free)} ({percent:.0f} %)")
        access = t("auth.storage.read_only") if row.mount.read_only else t("auth.storage.read_write")
        if row.mount.network:
            access += " · " + t("auth.storage.network")
        held = ", ".join(t(COMPONENT_LABELS[label]) for label in row.components)
        lines.append(
            "<tr>"
            f"<td><code>{escape_text(row.mount.point)}</code></td>"
            f"<td>{escape_text(row.mount.device)}</td>"
            f"<td>{escape_text(row.mount.fstype)}</td>"
            f"<td>{size}</td><td>{free}</td>"
            f"<td>{escape_text(access)}</td>"
            f"<td>{escape_text(held)}</td>"
            "</tr>"
        )

    body = (
        f"<table><tr>{head}</tr>{''.join(lines)}</table>"
        if lines
        else f'<p>{escape_text(t("auth.storage.none"))}</p>'
    )
    return (
        '<section class="auth-settings">'
        f'<h2>{escape_text(t("auth.storage.heading"))}</h2>'
        f'<p>{escape_text(t("auth.storage.intro"))}</p>'
        f"{body}"
        "</section>"
        f"{location_section(request, t, rows)}"
    )


def _in_container() -> bool:
    return config_dir() is not None


def _owner() -> str:
    return f"{os.getuid()}:{os.getgid()}"


def location_section(request: Request, t: Translator, rows: list[MountRow]) -> str:
    """Where the data lives, where it is to go, and how to move it."""

    generated_dir: Path = request.app.state.generated_dir
    location = data_location.load(request.app.state.paths.data_location)
    environment = dict(os.environ)
    in_container = _in_container()
    state = data_location.state(location, generated_dir, in_container, environment)
    session = current_session(request)
    token = escape_text(session.csrf) if session is not None else ""

    host_path = environment.get(data_location.DATA_DIR_ENV, "") if in_container else ""
    where = escape_text(str(generated_dir)) + (
        escape_text(t("auth.storage.location.host_path", path=host_path)) if host_path else ""
    )
    parts = [
        f'<section class="auth-settings" id="{LOCATION_ANCHOR}">',
        f'<h2>{escape_text(t("auth.storage.location.heading"))}</h2>',
        f'<p>{escape_text(t("auth.storage.location.intro"))}</p>',
    ]
    notice = LOCATION_NOTICES.get(request.query_params.get("storage", ""))
    if notice is not None:
        colours = "#fdecea;border:1px solid #f5c2c0" if ".refused." in notice else "#e8f5e9;border:1px solid #a5d6a7"
        parts.append(
            f'<p style="padding:.6rem .9rem;border-radius:6px;background:{colours}">{escape_text(t(notice))}</p>'
        )
    parts += [
        "<table>",
        f'<tr><td>{escape_text(t("auth.storage.location.current"))}</td><td><code>{where}</code></td></tr>',
        f'<tr><td>{escape_text(t("auth.storage.location.state_label"))}</td><td>{escape_text(t(STATE_LABELS[state]))}</td></tr>',
    ]
    if location is not None:
        parts.append(
            f'<tr><td>{escape_text(t("auth.storage.location.chosen"))}</td>'
            f"<td><code>{escape_text(location.target)}</code> — "
            f'{escape_text(t("auth.storage.location.chosen_by", name=location.chosen_by, when=location.chosen_at))}</td></tr>'
        )
    parts.append("</table>")

    writable = [row.mount.point for row in rows if not row.mount.read_only or in_container]
    options = "".join(f'<option value="{escape_text(point)}">' for point in writable)
    parts.append(
        f'<form method="post" action="{LOCATION_PATH}" style="display:flex;gap:.5rem;flex-wrap:wrap;align-items:center">'
        f'<input type="hidden" name="csrf" value="{token}">'
        f'<input type="text" name="target" list="aistack-mounts" size="40" required '
        f'value="{escape_text(location.target if location else "")}" '
        f'placeholder="{escape_text(t("auth.storage.location.placeholder"))}" '
        f'title="{escape_text(t("auth.storage.location.tooltip.target"))}">'
        f'<datalist id="aistack-mounts">{options}</datalist>'
        f'<button type="submit" name="action" value="save" '
        f'title="{escape_text(t("auth.storage.location.tooltip.save"))}">{escape_text(t("auth.storage.location.save"))}</button>'
        "</form>"
    )
    if location is not None:
        parts.append(
            f'<form method="post" action="{LOCATION_PATH}" style="margin-top:.5rem">'
            f'<input type="hidden" name="csrf" value="{token}">'
            f'<button type="submit" name="action" value="clear" '
            f'title="{escape_text(t("auth.storage.location.tooltip.clear"))}">{escape_text(t("auth.storage.location.clear"))}</button>'
            "</form>"
        )
    if location is not None and state == data_location.PLANNED:
        lines = data_location.commands(
            location, generated_dir, in_container=in_container, environment=environment, owner=_owner()
        )
        how = "auth.storage.location.how_container" if in_container else "auth.storage.location.how_systemd"
        back = "auth.storage.location.back_container" if in_container else "auth.storage.location.back_systemd"
        parts += [
            f"<p>{escape_text(t(how))}</p>",
            '<pre style="white-space:pre-wrap;word-break:break-all;background:#f4f6f9;'
            'border:1px solid #dde4ed;border-radius:6px;padding:.6rem .8rem">' + escape_text("\n".join(lines)) + "</pre>",
            f'<p class="note">{escape_text(t(back, old=str(generated_dir) + ".avant-deplacement", target=location.target))}</p>',
        ]
    parts.append("</section>")
    return "".join(parts)


@router.post(LOCATION_PATH, include_in_schema=False, dependencies=[ADMIN_ACTION])
def choose_location(request: Request, target: str = Form(""), action: str = Form("save")) -> Response:
    """Record where the data is to go — or forget the choice."""

    path: Path = request.app.state.paths.data_location
    if action == "clear":
        data_location.clear(path)
        return _back("cleared")

    generated_dir: Path = request.app.state.generated_dir
    try:
        cleaned = data_location.checked(
            target,
            generated_dir,
            size=data_location.measured_size(generated_dir),
            free_space=data_location.free_space(target.strip()) if target.strip().startswith("/") else None,
        )
    except data_location.LocationRefused as refused:
        return _back(refused.reason.rsplit(".", 1)[-1])

    session = current_session(request)
    data_location.save(
        path,
        data_location.DataLocation(
            target=cleaned,
            chosen_by=(session.name or session.subject) if session is not None else "",
            chosen_at=data_location.now(),
        ),
    )
    return _back("saved")


def _back(status: str) -> RedirectResponse:
    return RedirectResponse(f"/settings?storage={quote(status)}#{LOCATION_ANCHOR}", status_code=303)
