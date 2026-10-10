from __future__ import annotations

from dataclasses import dataclass

# Backup engines actually in use:
# - `DUMP_SQL`: a live database dumped without stopping the service
#   (mysqldump, mariadb-dump --single-transaction).
# - `STOP_AND_ARCHIVE`: the service is stopped, its data archived, then
#   restarted.
# - `LIVE_FILE_BACKUP`: plain files backed up while the service runs
#   (e.g. a restic snapshot).
DUMP_SQL = "dump_sql"
STOP_AND_ARCHIVE = "stop_and_archive"
LIVE_FILE_BACKUP = "live_file_backup"

ENGINES = (DUMP_SQL, STOP_AND_ARCHIVE, LIVE_FILE_BACKUP)


@dataclass(frozen=True)
class BackupStrategyDeclaration:
    """
    One service's declared backup strategy (OPS-0010): whether it holds
    persistent state and which mechanisms cover it.

    Declared by the owner, never inferred from a live system. `engines`
    may name several (e.g. a SQL dump plus a file backup). A stateful
    service with no engine is a real "no known backup" gap, reported by
    `aistack.runtime.uncovered_state_gap.find_uncovered_state`.
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
        """Whether a known backup mechanism covers this service's state."""

        return bool(self.engines)
