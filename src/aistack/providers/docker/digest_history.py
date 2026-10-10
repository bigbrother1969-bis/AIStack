from __future__ import annotations

import json
from pathlib import Path

from aistack.generators.history import write_artifact_with_history

# One subdirectory per subject, written on change like `diff_history`:
# the new digest is compared with the subject's "latest" file.
DEFAULT_GENERATED_DIR = Path("reports/generated")

DIGEST_DIRNAME = "docker-digest"
STEM = "docker-digest"


def _output_path(subject: str, generated_dir: Path) -> Path:
    """`generated_dir/docker-digest/<subject>/docker-digest.json`; a
    `project/service` subject nests one directory deeper."""

    return generated_dir / DIGEST_DIRNAME / subject / f"{STEM}.json"


def _read_previous_digest(output_path: Path) -> str | None:
    """The digest last recorded for the subject, or `None` when the file is
    missing or unreadable."""

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
    """True when `digest` differs from what was last recorded for
    `subject`. Read-only; used by `docker_digest_monitor --dry-run`."""

    return _read_previous_digest(_output_path(subject, generated_dir)) != digest


def record_image_digest(
    subject: str,
    digest: str,
    *,
    image: str = "",
    repo_digests: tuple[str, ...] | list[str] = (),
    generated_dir: Path = DEFAULT_GENERATED_DIR,
) -> Path | None:
    """Persist a subject's image digest to history when it changed (a
    changed digest means an upgrade); otherwise write nothing and return
    `None`."""

    if not has_changed(subject, digest, generated_dir=generated_dir):
        return None

    output_path = _output_path(subject, generated_dir)
    record: dict[str, object] = {"subject": subject, "digest": digest}
    # What a rollback needs once the image is gone from disk: its name
    # and the registry digests `docker pull` can fetch (`ADR-0018`).
    if image:
        record["image"] = image
    if repo_digests:
        record["repo_digests"] = list(repo_digests)
    content = json.dumps(record, indent=2, ensure_ascii=False) + "\n"

    latest_path, _ = write_artifact_with_history(content, output_path)

    return latest_path


REGISTRY_FILE = "registry-digests.json"


def known_repo_digests(subject: str, digest: str, *, generated_dir: Path = DEFAULT_GENERATED_DIR) -> list[str] | None:
    """The registry digests remembered for one image of `subject`, or
    None when that image was never looked up (`ADR-0018`)."""

    path = generated_dir / DIGEST_DIRNAME / subject / REGISTRY_FILE
    try:
        known = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = known.get(digest) if isinstance(known, dict) else None
    return [str(item) for item in value] if isinstance(value, list) else None


def remember_repo_digests(
    subject: str, digest: str, repo_digests: list[str], *, generated_dir: Path = DEFAULT_GENERATED_DIR
) -> None:
    """Store the registry digests of one image of `subject` in a side file
    (the history is untouched), so today's image can be pulled again
    after the next upgrade."""

    path = generated_dir / DIGEST_DIRNAME / subject / REGISTRY_FILE
    try:
        known = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        known = {}
    if not isinstance(known, dict):
        known = {}
    known[digest] = list(repo_digests)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(known, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
