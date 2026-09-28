from __future__ import annotations

import json
from pathlib import Path

from aistack.generators.history import write_artifact_with_history

# One subdirectory per subject, not one shared batch file the way
# `aistack.providers.docker.events_history` writes — a real fork from
# that stream's own shape, decided by what each one's own "write on
# change" actually compares. Docker events are individually new by
# nature (an event that already happened is never reported twice by
# `docker events` itself), so that stream only ever asks "is there
# anything at all this cycle" — `record_docker_events` returns `None`
# on an empty list and nothing more. A `docker diff` snapshot is
# cumulative and, for a quiet container, often *identical* to the
# last poll — the real question here is "did the value change", which
# needs something to compare the new snapshot against. Reading the
# stable "latest" file `write_artifact_with_history` already keeps
# per subject is that comparison, with no second, separate checkpoint
# state to keep in sync with it.
DEFAULT_GENERATED_DIR = Path("reports/generated")

DIFF_DIRNAME = "docker-diff"
STEM = "docker-diff"


def _output_path(subject: str, generated_dir: Path) -> Path:
    """
    `generated_dir / "docker-diff" / <subject> / "docker-diff.json"`.
    `subject` may itself embed a `/` (a Compose `project/service`
    pair, § 3) — `Path.__truediv__` on a string containing one simply
    nests one directory deeper, exactly as if it had been written
    out as two separate components; no escaping needed, and
    `aistack.timemachine.projection.docker_diff`'s own walk is built
    to find and reverse this nesting regardless of its depth.
    """

    return generated_dir / DIFF_DIRNAME / subject / f"{STEM}.json"


def _read_previous_changes(output_path: Path) -> list[dict[str, str]] | None:
    """
    Whatever `changes` list this subject's own stable "latest" file
    last held, or `None` — no such file yet (this subject's first
    observation ever), or its content does not parse as this stream's
    own shape. Deliberately not distinguished from each other by the
    caller: either way, there is nothing to compare the new snapshot
    against, so the new one is worth writing regardless of whether it
    is itself empty.
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
    """
    `True` when `changes` differs from whatever was last recorded for
    `subject` — the read-only half of `record_docker_diff`'s own
    comparison, exposed on its own so a caller (`aistack.cli
    .docker_diff_monitor`'s own `--dry-run`) can report what *would*
    be recorded without writing anything, the same distinction
    `aistack.cli.docker_events_monitor --dry-run` already draws for
    its own stream.
    """

    return _read_previous_changes(_output_path(subject, generated_dir)) != changes


def record_docker_diff(
    subject: str,
    changes: list[dict[str, str]],
    *,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
) -> Path | None:
    """
    Persist one subject's current `docker diff` snapshot to history —
    but only when `has_changed` says it actually differs from what
    was last recorded for that same subject. Cadrage decision 4
    (`aistack.providers.docker.diff`'s own module comment): the full
    current listing, never an invented delta — this compares two full
    listings for equality, it does not compute one.

    Returns `None`, writing nothing, when the new `changes` list is
    identical to the previous one — the same "write on change" economy
    `aistack.priority.decision_history.record_decision` already holds
    for a different comparison (`ApplyReport.changed`, computed by its
    own caller rather than read back from disk); this is the first
    stream in this package whose own "did it change" question needs a
    read-back rather than a value the caller already has in hand,
    since a `docker diff` snapshot's own novelty can only be known by
    comparing it to what came before.
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
