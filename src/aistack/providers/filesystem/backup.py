from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from aistack.contracts.backup_reading import BackupReading


class BackupProvider:
    """Observe the newest file in each declared backup location, without
    drawing conclusions (`OPS-0006`).

    Never raises. A path that does not exist is skipped, but an existing
    path with no file still yields a reading (`newest_file_mtime=None`):
    "never received a backup" is exactly what this domain must surface.
    """

    provider_id = "aistack.provider.backup"
    provider_name = "Backup Provider"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def collect_freshness(
        self, paths: tuple[str, ...]
    ) -> tuple[BackupReading, ...]:
        """Freshness of each path the caller declares (`OPS-0006`).

        Missing paths are skipped; an existing path with no file gives
        `newest_file_mtime=None`.
        """

        readings: list[BackupReading] = []

        for raw_path in paths:
            directory = Path(raw_path)

            # An unreadable path (e.g. an on-demand disk currently
            # unmounted: "No such device") yields a reading with the
            # problem, not a skip or a crash. A `hard` NFS mount whose
            # server is down blocks `stat` forever, so the scan is
            # bounded by `self.timeout`.
            outcome = _scan_within(directory, self.timeout)
            if isinstance(outcome, OSError):
                present, newest = True, None
                problem = outcome.strerror or type(outcome).__name__
            elif outcome is None:
                present, newest = True, None
                problem = f"no answer within {self.timeout:g} s"
            else:
                present, newest = outcome
                problem = ""
            if not present:
                continue
            if problem:
                readings.append(
                    BackupReading(
                        path=raw_path,
                        observed_at=datetime.now(timezone.utc),
                        newest_file_mtime=None,
                        unreachable=problem,
                    )
                )
                continue

            readings.append(
                BackupReading(
                    path=raw_path,
                    observed_at=datetime.now(timezone.utc),
                    newest_file_mtime=(
                        datetime.fromtimestamp(newest, tz=timezone.utc)
                        if newest is not None
                        else None
                    ),
                )
            )

        return tuple(readings)


def _scan_within(directory: Path, timeout: float) -> tuple[bool, float | None] | OSError | None:
    """`_scan`'s result, the OSError it raised, or None when it did not
    answer in time. A daemon thread: one blocked on a dead NFS server
    never keeps the process from exiting."""

    box: list[tuple[bool, float | None] | OSError] = []

    def run() -> None:
        try:
            box.append(_scan(directory))
        except OSError as error:
            box.append(error)

    worker = threading.Thread(target=run, name="aistack-backup-scan", daemon=True)
    worker.start()
    worker.join(timeout)
    return box[0] if box else None


def _scan(directory: Path) -> tuple[bool, float | None]:
    """Whether `directory` exists, and its newest file's mtime."""

    if not directory.exists():
        return False, None
    return True, _newest_mtime(directory)


def _newest_mtime(directory: Path) -> float | None:
    newest: float | None = None
    for candidate in directory.rglob("*"):
        try:
            if not candidate.is_file():
                continue
            mtime = candidate.stat().st_mtime
        except OSError:
            continue
        if newest is None or mtime > newest:
            newest = mtime
    return newest
