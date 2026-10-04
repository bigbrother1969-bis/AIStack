"""
Settings' "Disks and mounts" section, for an administrator (asked by
the owner, 2026-10-04): every real mount the host sees, its size, free
space and access, and which of AIStack's own components lives on it.
Seeing only — choosing where each component goes is 1.8's.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import Request

from aistack.host.mounts import MountRow, disks_and_mounts
from aistack.i18n import Translator
from aistack.renderers.text import escape_text

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
    )
