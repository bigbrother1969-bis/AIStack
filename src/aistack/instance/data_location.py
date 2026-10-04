"""
Where AIStack keeps its data — `reports/generated`, as one block — and
where the owner chose to move it (1.8, decided by the owner 2026-10-04:
one choice for the whole directory; AIStack records it and says what to
run, it never moves anything itself).

The choice is a small file next to the declarations —
`data_location.yml` in the configuration directory, else at the
checkout's root (ignored by git: it says where this host's data goes,
not how AIStack works). It names the directory chosen, who chose it and
when.

**Done or planned.** A git installation reads its data through
`reports/generated`; once moved, that path is a link to the chosen
directory, so the move is done when the path resolves there. In the
container the application always sees `/app/reports/generated`; the
host directory behind it is `AISTACK_DATA_DIR`, which `docker-compose.yml`
mounts and passes in: the move is done when it names the chosen one.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from aistack.host.mounts import MountRow

FILE_NAME = "data_location.yml"
# The directory the data goes to, at the root of the disk chosen.
DATA_FOLDER = "aistack-data"
# A container's own mounts, never offered.
CONTAINER_OWN = ("/config", "/app", "/var/run", "/etc")
DATA_DIR_ENV = "AISTACK_DATA_DIR"

NONE = "none"
PLANNED = "planned"
DONE = "done"

# Room to spare beyond the data's own size.
MARGIN = 1.1
# Measuring the data's size walks every file: never longer than this.
SIZE_BUDGET_SECONDS = 5.0

_HEADER = """\
# AIStack — where its data (`reports/generated`) is to live, chosen
# from Settings (1.8). Written by the application; AIStack never moves
# the data itself: Settings shows the commands to run.
"""


@dataclass(frozen=True)
class DataLocation:
    target: str
    chosen_by: str = ""
    chosen_at: str = ""


class LocationRefused(Exception):
    """A choice that cannot be recorded; `reason` is an i18n key."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def location_file(config_dir: Path | None, repository_root: Path) -> Path:
    return (config_dir if config_dir is not None else repository_root) / FILE_NAME


def load(path: Path) -> DataLocation | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict) or not str(data.get("target") or "").strip():
        return None
    return DataLocation(
        target=str(data["target"]).strip(),
        chosen_by=str(data.get("chosen_by") or ""),
        chosen_at=str(data.get("chosen_at") or ""),
    )


def save(path: Path, location: DataLocation) -> None:
    body = yaml.safe_dump(
        {"target": location.target, "chosen_by": location.chosen_by, "chosen_at": location.chosen_at},
        allow_unicode=True,
        sort_keys=False,
    )
    path.write_text(_HEADER + body, encoding="utf-8")


def clear(path: Path) -> None:
    path.unlink(missing_ok=True)


def measured_size(directory: Path, budget: float = SIZE_BUDGET_SECONDS) -> int | None:
    """The size of every file under `directory`, or None when walking it
    takes longer than `budget`."""

    started = time.monotonic()
    total = 0
    for root, _dirs, files in os.walk(directory):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                continue
        if time.monotonic() - started > budget:
            return None
    return total


def target_on(mount: str) -> str:
    """The directory the data goes to on the disk mounted at `mount`."""

    return mount.rstrip("/") + "/" + DATA_FOLDER


def mount_of(path: Path, points: list[str]) -> str | None:
    """The mount point `path` lives under: the longest one containing it."""

    text = str(path)
    found = [point for point in points if point == "/" or text == point or text.startswith(point.rstrip("/") + "/")]
    return max(found, key=len) if found else None


def candidates(rows: list[MountRow], generated_dir: Path, in_container: bool) -> list[MountRow]:
    """
    The disks the data may be moved to, as the list Settings offers:
    every real mount the process can write to — in the container, every
    host directory it mounts, read-only there but not on the host —
    except a network share (the sessions are a SQLite file, which a
    network share does not keep safely), the disk the data is already
    on, and the container's own mounts.
    """

    points = [row.mount.point for row in rows]
    try:
        current = None if in_container else mount_of(generated_dir.resolve(), points)
    except OSError:
        current = None
    return [
        row
        for row in rows
        if not row.mount.network
        and (in_container or not row.mount.read_only)
        and row.mount.point != current
        and not any(row.mount.point == own or row.mount.point.startswith(own + "/") for own in CONTAINER_OWN)
    ]


def checked(
    mount: str,
    offered: list[MountRow],
    *,
    size: int | None,
) -> str:
    """The directory the data goes to on `mount`, when `mount` is one of
    the disks offered and has room for it; else `LocationRefused`."""

    row = next((row for row in offered if row.mount.point == mount), None)
    if row is None:
        raise LocationRefused("auth.storage.location.refused.unknown")
    if size is not None and row.usage is not None and row.usage.free < size * MARGIN:
        raise LocationRefused("auth.storage.location.refused.space")
    return target_on(mount)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def state(location: DataLocation | None, generated_dir: Path, in_container: bool, environment: dict[str, str]) -> str:
    if location is None:
        return NONE
    if in_container:
        declared = environment.get(DATA_DIR_ENV, "").rstrip("/")
        return DONE if declared == location.target else PLANNED
    try:
        return DONE if generated_dir.resolve() == Path(location.target).resolve() else PLANNED
    except OSError:
        return PLANNED


SYSTEMD_UNITS = (
    "aistack-web",
    "aistack-docker-events-monitor",
    "aistack-docker-diff-monitor",
    "aistack-docker-digest-monitor",
    "aistack-docker-packages-monitor",
    "aistack-resource-priority-monitor",
)


def commands(
    location: DataLocation,
    generated_dir: Path,
    *,
    in_container: bool,
    environment: dict[str, str],
    owner: str,
) -> list[str]:
    """What the owner runs to move the data, in order."""

    target = location.target
    if in_container:
        source = environment.get(DATA_DIR_ENV, "").rstrip("/") or "./data"
        return [
            "docker compose down",
        f"sudo mkdir -p {target}",
            f"sudo rsync -aH --info=progress2 {source}/ {target}/",
            f"sudo chown -R {owner} {target}",
            f"grep -q '^{DATA_DIR_ENV}=' .env && sed -i 's|^{DATA_DIR_ENV}=.*|{DATA_DIR_ENV}={target}|' .env"
            f" || echo '{DATA_DIR_ENV}={target}' >> .env",
            "docker compose up -d",
        ]
    current = str(generated_dir)
    units = " ".join(SYSTEMD_UNITS)
    return [
        f"sudo systemctl stop {units}",
        # The one tracked file under it (GH-0002's debt report): git
        # stops reporting it deleted once its directory is a link.
        f"git -C {generated_dir.parent.parent} update-index --skip-worktree reports/generated/repository-debt-report.md",
        f"sudo mkdir -p {target}",
        f"sudo rsync -aH --info=progress2 {current}/ {target}/",
        f"sudo chown -R {owner} {target}",
        f"mv {current} {current}.avant-deplacement",
        f"ln -s {target} {current}",
        f"sudo systemctl start {units}",
    ]
