from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history

# One subdirectory per subject, the same write-on-change shape
# `aistack.providers.docker.digest_history` and `.diff_history` already
# hold, applied here to a `{mechanism, packages}` pair instead of a
# single string or a list of changes: a package inventory is a single
# current snapshot, not individually-novel the way a Docker event is,
# so "did it change" needs the same stable "latest" file
# `write_artifact_with_history` already keeps per subject.
DEFAULT_GENERATED_DIR = Path("reports/generated")

PACKAGES_DIRNAME = "docker-packages"
STEM = "docker-packages"


def _output_path(subject: str, generated_dir: Path) -> Path:
    """
    `generated_dir / "docker-packages" / <subject> / "docker-packages.json"`
    — the same nesting `aistack.providers.docker.digest_history
    ._output_path` already holds for a subject that may itself embed a
    `/` (a Compose `project/service` pair, § 3); `aistack.timemachine
    .projection.docker_packages`'s own walk reverses it the same way
    that stream's own projector already does.
    """

    return generated_dir / PACKAGES_DIRNAME / subject / f"{STEM}.json"


def _read_previous(output_path: Path) -> dict[str, Any] | None:
    """
    Whatever `{"mechanism", "packages"}` this subject's own stable
    "latest" file last held, or `None` — no such file yet, or its
    content does not parse as this stream's own shape. Not
    distinguished from each other by the caller, the same restraint
    every other write-on-change stream in this package already holds.
    """

    try:
        parsed = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(parsed, dict):
        return None

    mechanism = parsed.get("mechanism")
    packages = parsed.get("packages")
    if not isinstance(mechanism, str) or not isinstance(packages, list):
        return None

    return {"mechanism": mechanism, "packages": packages}


def has_changed(
    subject: str,
    mechanism: str,
    packages: list[dict[str, str]],
    *,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
) -> bool:
    """
    `True` when `(mechanism, packages)` differs from whatever was last
    recorded for `subject` — the read-only half of
    `record_package_inventory`'s own comparison, exposed on its own so
    a caller (`aistack.cli.docker_packages_monitor`'s own `--dry-run`)
    can report what *would* be recorded without writing anything, the
    same distinction every other stream in this package already draws.

    A mechanism change alone (e.g. `"dpkg"` to `"none"`, a container
    whose own package database became unreadable) counts as a change
    even when `packages` happens to compare equal (both empty) — the
    mechanism that answered is itself part of what this stream states,
    the same reasoning `aistack.providers.docker.packages`'s own
    module comment gives for recording it at all.
    """

    previous = _read_previous(_output_path(subject, generated_dir))
    if previous is None:
        return True

    return previous != {"mechanism": mechanism, "packages": packages}


def record_package_inventory(
    subject: str,
    mechanism: str,
    packages: list[dict[str, str]],
    *,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
) -> Path | None:
    """
    Persist one subject's current package inventory to history — but
    only when `has_changed` says it actually differs from what was
    last recorded for that same subject.

    Returns `None`, writing nothing, when the new observation is
    identical to the previous one — the same "write on change" economy
    every other stream in this package already holds.
    """

    if not has_changed(subject, mechanism, packages, generated_dir=generated_dir):
        return None

    output_path = _output_path(subject, generated_dir)
    content = (
        json.dumps(
            {"subject": subject, "mechanism": mechanism, "packages": packages},
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    latest_path, _ = write_artifact_with_history(content, output_path)

    return latest_path
