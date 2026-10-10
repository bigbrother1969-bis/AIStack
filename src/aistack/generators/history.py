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

    Every copy is kept, with no retention window or count cap. Returns
    `(latest_path, history_path)`.

    The stamp uses `strftime` rather than `isoformat` because a path
    cannot carry `:`. Two writes in the same second get a numeric
    suffix so the second never overwrites the first.
    """

    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(content, encoding="utf-8")

    history_dir = latest_path.parent / "history" / latest_path.stem
    history_dir.mkdir(parents=True, exist_ok=True)

    stamp = wall_clock().strftime("%Y-%m-%dT%H-%M-%SZ")
    history_path = history_dir / f"{stamp}{latest_path.suffix}"
    suffix = 1
    while history_path.exists():
        history_path = history_dir / f"{stamp}-{suffix}{latest_path.suffix}"
        suffix += 1
    history_path.write_text(content, encoding="utf-8")

    return latest_path, history_path
