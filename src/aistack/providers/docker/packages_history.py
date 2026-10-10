from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history

# One subdirectory per subject, written on change like `diff_history`:
# the new `{mechanism, packages}` snapshot is compared with the subject's
# "latest" file.
DEFAULT_GENERATED_DIR = Path("reports/generated")

PACKAGES_DIRNAME = "docker-packages"
STEM = "docker-packages"


def _output_path(subject: str, generated_dir: Path) -> Path:
    """`generated_dir/docker-packages/<subject>/docker-packages.json`; a
    `project/service` subject nests one directory deeper."""

    return generated_dir / PACKAGES_DIRNAME / subject / f"{STEM}.json"


def _read_previous(output_path: Path) -> dict[str, Any] | None:
    """The `{"mechanism", "packages"}` last recorded for the subject, or
    `None` when the file is missing or unreadable."""

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
    """True when `(mechanism, packages)` differs from what was last
    recorded for `subject`. Read-only; used by `docker_packages_monitor
    --dry-run`.

    A mechanism change alone (e.g. `"dpkg"` to `"none"`) counts as a
    change.
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
    """Persist a subject's package inventory to history when it changed;
    otherwise write nothing and return `None`."""

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
