from __future__ import annotations

from dataclasses import dataclass

# The only backup engines this heritage has ever actually seen in use
# — grounded in real precedent, found and confirmed during the 1.6
# tranche 2 cadrage (R9, 2026-09-30), never a speculative, general
# "backup engine" taxonomy (`ARC-P-006`):
#
# - `DUMP_SQL` — a live database dumped without stopping the service
#   (`backup-wordpress.sh`'s `mysqldump`; `backup_raspberry.sh`'s
#   `mariadb-dump --single-transaction` for Vikunja).
# - `STOP_AND_ARCHIVE` — the service is stopped, its configuration
#   archived, then restarted (`backup-arrstack.sh`).
# - `LIVE_FILE_BACKUP` — plain files backed up while the service keeps
#   running, no stop and no database dump (`backup_raspberry.sh`'s
#   restic snapshot of six SQLite-backed stacks).
#
# The roadmap's own R9 names only the first two as examples ("dump SQL
# pour une base vivante, arrêt + archive pour une configuration") —
# `LIVE_FILE_BACKUP` is added here because it is a third real
# mechanism already running (Raspberry, restic), not a hypothetical
# fourth case invented ahead of one.
DUMP_SQL = "dump_sql"
STOP_AND_ARCHIVE = "stop_and_archive"
LIVE_FILE_BACKUP = "live_file_backup"

ENGINES = (DUMP_SQL, STOP_AND_ARCHIVE, LIVE_FILE_BACKUP)


@dataclass(frozen=True)
class BackupStrategyDeclaration:
    """
    One service's own declared backup strategy — `OPS-0010`'s "état
    persistant" record (R9): does this service hold persistent state
    at all, and if so, which real, already-running mechanism (or
    mechanisms) cover it.

    **Not a live observation — a declared record, read as one.** The
    same "declared, not collected" split `PraTestReading` already
    holds (`OPS-0009`): there is no provider that can discover
    whether a service's data is stateful, or which script backs it
    up — the owner states it, this type carries what was stated
    (`GOV-P-001`). `has_state`/`engines`/`mechanism` are never
    inferred from `service_categorization.yml` or from any live
    system.

    `engines` may name more than one — Vikunja's own real mechanism
    is both a `DUMP_SQL` (its MariaDB dump) and a `LIVE_FILE_BACKUP`
    (its files, via restic) — so this is not "the one engine a
    service uses" but "every engine actually confirmed to cover it".

    `covered` (below) is exactly what `find_uncovered_state`
    (`aistack.runtime.uncovered_state_gap`) asks of every declaration
    with `has_state=True`: a stateful service with no engine declared
    is not "unknown whether it is backed up" — it is a real, honest
    "no known backup mechanism for this service's state", exactly the
    way `PraTestReading.status is None` states "never tested" rather
    than leaving the question open. Two services in `OPS-0010`'s own
    declared file (`nextcloud`, `immich`) and one host
    (`gigabyte`) are declared exactly this way — a real, confirmed gap
    in what this session could ground, not a placeholder to fill in
    later.
    """

    service: str
    host: str
    has_state: bool
    engines: tuple[str, ...] = ()
    mechanism: str | None = None

    def __post_init__(self) -> None:
        if not self.service.strip():
            raise ValueError("a backup strategy declaration names no service")

        if not self.host.strip():
            raise ValueError(f"{self.service} declares no host")

        unknown = [engine for engine in self.engines if engine not in ENGINES]

        if unknown:
            raise ValueError(
                f"{self.service} declares an unknown engine {unknown!r} — "
                f"known: {', '.join(ENGINES)}"
            )

        if len(set(self.engines)) != len(self.engines):
            raise ValueError(
                f"{self.service} declares the same engine more than once "
                f"in {self.engines}"
            )

        if not self.has_state and self.engines:
            raise ValueError(
                f"{self.service} declares no persistent state but names "
                f"{len(self.engines)} backup engine(s) — a stateless "
                f"service needs no backup engine declared for it"
            )

        if self.engines and self.mechanism is None:
            raise ValueError(
                f"{self.service} declares {len(self.engines)} backup "
                f"engine(s) but no mechanism describing them"
            )

        if self.mechanism is not None and not self.mechanism.strip():
            raise ValueError(f"{self.service} declares a blank mechanism")

    @property
    def covered(self) -> bool:
        """
        Whether a known backup mechanism actually covers this
        service's persistent state. A stateless service is never
        asked this question — `find_uncovered_state` only evaluates
        declarations with `has_state=True`.
        """

        return bool(self.engines)
