from __future__ import annotations

import json
from pathlib import Path

from aistack.generators.history import write_artifact_with_history

# One subdirectory per subject: a `docker diff` snapshot is cumulative and
# often identical to the last one, so writing on change means comparing
# with that subject's "latest" file.
DEFAULT_GENERATED_DIR = Path("reports/generated")

DIFF_DIRNAME = "docker-diff"
STEM = "docker-diff"


def _output_path(subject: str, generated_dir: Path) -> Path:
    """`generated_dir/docker-diff/<subject>/docker-diff.json`.

    A `project/service` subject nests one directory deeper;
    `aistack.timemachine.projection.docker_diff` handles any depth.
    """

    return generated_dir / DIFF_DIRNAME / subject / f"{STEM}.json"


def _read_previous_changes(output_path: Path) -> list[dict[str, str]] | None:
    """The `changes` list in the subject's latest file, or `None` when the
    file is missing or unreadable (then the new snapshot is always written).
    """

    try:
        parsed = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    changes = parsed.get("changes") if isinstance(parsed, dict) else None
    return changes if isinstance(changes, list) else None


def has_changed(
    subject: str,
    changes: list[dict[str, str]],
    *,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
) -> bool:
    """True when `changes` differs from what was last recorded for
    `subject`. Read-only; used by `docker_diff_monitor --dry-run`.
    """

    return _read_previous_changes(_output_path(subject, generated_dir)) != changes


def record_docker_diff(
    subject: str,
    changes: list[dict[str, str]],
    *,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
) -> Path | None:
    """Persist a subject's full `docker diff` listing to history when it
    differs from the last one recorded; otherwise write nothing and return
    `None`.
    """

    if not has_changed(subject, changes, generated_dir=generated_dir):
        return None

    output_path = _output_path(subject, generated_dir)
    content = (
        json.dumps(
            {"subject": subject, "changes": changes},
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    latest_path, _ = write_artifact_with_history(content, output_path)

    return latest_path
