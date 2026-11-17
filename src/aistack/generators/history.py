from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def wall_clock() -> datetime:
    """The instant a history copy is stamped with. One function, so
    `aistack.explications.human` reads the same clock and a test can
    replace it."""

    return datetime.now(timezone.utc)


def write_artifact_with_history(content: str, latest_path: Path) -> tuple[Path, Path]:
    """
    Write a generated artifact to `latest_path` and to a timestamped
    copy in `history/<stem>/` beside it (Observation History).

    A copy is kept for every observation that *differs* from the one
    before it. When `content` is byte for byte what `latest_path`
    already holds and that observation has a copy, no new copy is
    written and the existing newest one is returned: a reader asking
    what was observed at a later instant gets that copy anyway
    (`aistack.history.query` takes the newest observation at or before
    the instant), so nothing is lost, and a quiet host stops filling
    the disk with identical files (916 MB of them under
    `history/console` on 2026-11-07). No retention window or count cap
    otherwise. Returns `(latest_path, history_path)`.

    The stamp uses `strftime` rather than `isoformat` because a path
    cannot carry `:`. Two writes in the same second get a numeric
    suffix so the second never overwrites the first.
    """

    latest_path.parent.mkdir(parents=True, exist_ok=True)
    history_dir = latest_path.parent / "history" / latest_path.stem

    unchanged = _holds(latest_path, content)
    latest_path.write_text(content, encoding="utf-8")

    if unchanged:
        newest = _newest_copy(history_dir)
        if newest is not None:
            return latest_path, newest

    history_dir.mkdir(parents=True, exist_ok=True)

    stamp = wall_clock().strftime("%Y-%m-%dT%H-%M-%SZ")
    history_path = history_dir / f"{stamp}{latest_path.suffix}"
    suffix = 1
    while history_path.exists():
        history_path = history_dir / f"{stamp}-{suffix}{latest_path.suffix}"
        suffix += 1
    history_path.write_text(content, encoding="utf-8")

    return latest_path, history_path


def write_view(content: str, path: Path) -> Path:
    """
    Write a generated view whole, with no history: a page that shows
    this run and nothing older (`plan.html`).

    Written beside its final name and moved into place, so a reader
    never opens half a page. Returns `path`.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
    return path


def ensure_link(link_path: Path, target: Path) -> None:
    """
    Make `link_path` a relative symlink to `target`; idempotent.

    A real file there was put by hand, so it raises rather than overwrite it.
    """

    if link_path.is_symlink():
        if link_path.readlink() == target:
            return
        link_path.unlink()
    elif link_path.exists():
        raise ValueError(
            f"{link_path} already exists and is not a symlink this "
            f"command manages; remove it by hand before running "
            f"console_render again"
        )

    link_path.symlink_to(target)


def _holds(path: Path, content: str) -> bool:
    """Whether `path` already holds exactly `content`."""

    try:
        return path.read_text(encoding="utf-8") == content
    except (OSError, UnicodeDecodeError):
        return False


def _newest_copy(history_dir: Path) -> Path | None:
    """The most recently written history copy, or None when there is none
    (a first run, or a history someone cleared)."""

    if not history_dir.is_dir():
        return None
    copies = [path for path in history_dir.iterdir() if path.is_file()]
    if not copies:
        return None
    return max(copies, key=lambda path: (path.stat().st_mtime_ns, path.name))
