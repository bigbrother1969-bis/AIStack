from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from aistack.contracts.backup_reading import BackupReading


class BackupProvider:
    """
    Observe a declared backup location's own state, and conclude
    nothing.

    `PLAN-J7`'s fourth domain (Sauvegarde / PRA) — the owner's own
    stated requirement: "Vérifier qu'il existe réellement une
    sauvegarde, qu'elle est fonctionnelle et que les backup ne sont
    pas trop vieux." The same boundary (`ARC-P-012`) `StorageProvider`
    already holds, applied to a backup directory's newest file instead
    of a mount's used/free bytes.

    **Refines `StorageProvider.collect_usage`'s "never raises" convention,
    rather than repeating it verbatim.** A mount `StorageProvider`
    cannot reach at all — not currently mounted, does not exist — is
    silently skipped: no reading is produced for it, because there is
    nothing there to have an opinion about. `collect_freshness` skips
    a path the same way when it does not exist at all. But a path that
    *does* exist and holds no backup file is different: "this
    directory has never received a backup" is itself the fact this
    domain exists to surface (`OPS-0006`), not a reason to stay
    silent about it — so that case still produces a `BackupReading`,
    with `newest_file_mtime=None`. Skipping it the way `StorageProvider`
    skips an absent mount would silently drop the one case the owner
    asked this domain to catch.
    """

    provider_id = "aistack.provider.backup"
    provider_name = "Backup Provider"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def collect_freshness(
        self, paths: tuple[str, ...]
    ) -> tuple[BackupReading, ...]:
        """
        Every declared path's own freshness, in one call.

        `paths` is declared by the caller — `OPS-0006`'s own table,
        not this provider — the same "the caller says what to look
        at" `StorageProvider.collect_usage` already holds for
        `OPS-0005`'s mounts.

        A path that does not exist on this host at all is skipped —
        never raises, mirroring `StorageProvider.collect_usage`
        exactly for that case. A path that exists is always read into
        a reading, even when it holds no file: `newest_file_mtime`
        is then `None`, stating "no backup file found" rather than
        omitting the path from the result.
        """

        readings: list[BackupReading] = []

        for raw_path in paths:
            directory = Path(raw_path)

            # A path that exists but cannot be read — a disk mounted on
            # demand, seen from a container while it is unmounted
            # ("No such device", GIGABYTE 2026-10-08) — is a reading of
            # its own: never skipped as if absent, never a crash of the
            # whole render.
            #
            # And never a wait without end: the reference host's backup
            # disk is an NFS share of the Raspberry, mounted `hard` — if
            # the Raspberry is down, a stat blocks until it is back, and
            # the console is rendered at every start of the web
            # application. Past `self.timeout` seconds, the path is
            # reported as not answering.
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
