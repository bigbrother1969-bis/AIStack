from __future__ import annotations

import json
from pathlib import Path

from aistack.generators.history import write_artifact_with_history

# One subdirectory per subject, the same write-on-change shape
# `aistack.providers.docker.diff_history` already holds for the same
# reason (that module's own comment explains it in full): a digest
# observation is a single current value, not individually-novel the
# way a Docker event is, so "did it change" needs something to compare
# the new value against — the stable "latest" file
# `write_artifact_with_history` already keeps per subject, with no
# second, separate checkpoint state to keep in sync with it.
DEFAULT_GENERATED_DIR = Path("reports/generated")

DIGEST_DIRNAME = "docker-digest"
STEM = "docker-digest"


def _output_path(subject: str, generated_dir: Path) -> Path:
    """
    `generated_dir / "docker-digest" / <subject> / "docker-digest.json"`
    — the same nesting `aistack.providers.docker.diff_history
    ._output_path` already holds for a subject that may itself embed a
    `/` (a Compose `project/service` pair, § 3); `aistack.timemachine
    .projection.docker_digest`'s own walk reverses it the same way
    that stream's own projector already does.
    """

    return generated_dir / DIGEST_DIRNAME / subject / f"{STEM}.json"


def _read_previous_digest(output_path: Path) -> str | None:
    """
    Whatever `digest` this subject's own stable "latest" file last
    held, or `None` — no such file yet, or its content does not parse
    as this stream's own shape. Not distinguished from each other by
    the caller, the same restraint `aistack.providers.docker
    .diff_history._read_previous_changes` already holds: either way,
    there is nothing to compare the new value against, so it is worth
    writing regardless.
    """

    try:
        parsed = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    digest = parsed.get("digest") if isinstance(parsed, dict) else None
    return digest if isinstance(digest, str) else None


def has_changed(
    subject: str,
    digest: str,
    *,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
) -> bool:
    """
    `True` when `digest` differs from whatever was last recorded for
    `subject` — the read-only half of `record_image_digest`'s own
    comparison, exposed on its own so a caller
    (`aistack.cli.docker_digest_monitor`'s own `--dry-run`) can report
    what *would* be recorded without writing anything, the same
    distinction `aistack.providers.docker.diff_history.has_changed`
    already draws for its own stream.
    """

    return _read_previous_digest(_output_path(subject, generated_dir)) != digest


def record_image_digest(
    subject: str,
    digest: str,
    *,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
) -> Path | None:
    """
    Persist one subject's current image digest to history — but only
    when `has_changed` says it actually differs from what was last
    recorded for that same subject. A changed digest for a stable
    subject is, by cadrage decision 4
    (`aistack.providers.docker.digest`'s own module comment), the
    local proof an upgrade happened.

    Returns `None`, writing nothing, when the new `digest` is
    identical to the previous one — the same "write on change" economy
    `aistack.providers.docker.diff_history.record_docker_diff` already
    holds for its own stream.
    """

    if not has_changed(subject, digest, generated_dir=generated_dir):
        return None

    output_path = _output_path(subject, generated_dir)
    content = (
        json.dumps({"subject": subject, "digest": digest}, indent=2, ensure_ascii=False)
        + "\n"
    )

    latest_path, _ = write_artifact_with_history(content, output_path)

    return latest_path
