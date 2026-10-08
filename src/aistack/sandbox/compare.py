"""
Sandbox ↔ live comparison (`ADR-0018` § 7, owner's decisions
2026-10-08): what the restored backup holds next to what the service
holds now — rows per table, files per folder — as numbers, never as a
verdict. A backup taken last night is always a little behind; the
report shows by how much, the owner judges.

Read-only on the live side:
- files are walked on the host, never opened for writing;
- a database is asked `SELECT COUNT(*)` from inside its own live
  container, with that container's own environment — the password
  stays in the container, never on a command line AIStack builds, never
  in a report.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from aistack.sandbox.run import SandboxRun, StepFailed

# Counted in batches: one query per batch, not per table.
_BATCH = 40

MARIADB = (
    'P="${MARIADB_ROOT_PASSWORD:-$MYSQL_ROOT_PASSWORD}"; D="${DB:-${MARIADB_DATABASE:-$MYSQL_DATABASE}}"; '
    'MYSQL_PWD="$P" exec mariadb -uroot -N -B "$D" -e "$1"'
)
POSTGRES = (
    'PGPASSWORD="$POSTGRES_PASSWORD" exec psql -U "${POSTGRES_USER:-postgres}" '
    '-d "${DB:-$POSTGRES_DB}" -v ON_ERROR_STOP=1 -tA -F "|" -c "$1"'
)


def _ask(run: SandboxRun, container: str, engine: str, query: str, database: str) -> str:
    environment = ["-e", f"DB={database}"] if database else []
    result = run.docker("exec", *environment, container, "sh", "-c", engine, "sh", query, timeout=600)
    return result.stdout.strip()


def _tables(run: SandboxRun, container: str, engine: str, database: str) -> list[str]:
    query = (
        "SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE'"
        if engine == MARIADB
        else "SELECT tablename FROM pg_tables WHERE schemaname='public'"
    )
    return sorted(line for line in _ask(run, container, engine, query, database).splitlines() if line)


def _quote(engine: str, table: str) -> str:
    return f"`{table}`" if engine == MARIADB else '"' + table.replace('"', '""') + '"'


def _counts(run: SandboxRun, container: str, engine: str, tables: list[str], database: str) -> dict[str, int]:
    counted: dict[str, int] = {}
    separator = "\t" if engine == MARIADB else "|"
    for start in range(0, len(tables), _BATCH):
        batch = tables[start:start + _BATCH]
        query = " UNION ALL ".join(
            f"SELECT '{table}', COUNT(*) FROM {_quote(engine, table)}" for table in batch
        )
        for line in _ask(run, container, engine, query, database).splitlines():
            name, _, value = line.partition(separator)
            if value.strip().isdigit():
                counted[name] = int(value)
    return counted


def compare_tables(
    run: SandboxRun,
    *,
    engine: str,
    sandbox_container: str,
    sandbox_database: str,
    live_container: str,
    live_database: str = "",
) -> dict[str, Any]:
    """Rows per table, backup next to live, the biggest gaps first."""

    backup_tables = _tables(run, sandbox_container, engine, sandbox_database)
    live_tables = _tables(run, live_container, engine, live_database)
    common = sorted(set(backup_tables) & set(live_tables))
    backup = _counts(run, sandbox_container, engine, common, sandbox_database)
    live = _counts(run, live_container, engine, common, live_database)
    rows: list[dict[str, Any]] = [
        {"table": table, "backup": backup.get(table, 0), "live": live.get(table, 0),
         "gap": live.get(table, 0) - backup.get(table, 0)}
        for table in common
    ]
    rows.sort(key=lambda row: (-abs(int(row["gap"])), str(row["table"])))
    return {
        "tables_compared": len(common),
        "rows_backup": sum(backup.values()),
        "rows_live": sum(live.values()),
        "tables_differing": sum(1 for row in rows if row["gap"]),
        "only_in_backup": sorted(set(backup_tables) - set(live_tables)),
        "only_live": sorted(set(live_tables) - set(backup_tables)),
        "tables": rows,
    }


def _walk(root: Path) -> dict[str, tuple[int, int]]:
    """Files and bytes per first-level folder ('.' for files at the top)."""

    totals: dict[str, tuple[int, int]] = {}
    for directory, _, files in os.walk(root, onerror=lambda error: None):
        relative = Path(directory).relative_to(root)
        key = relative.parts[0] if relative.parts else "."
        count, size = totals.get(key, (0, 0))
        for name in files:
            try:
                size += (Path(directory) / name).lstat().st_size
            except OSError:
                pass
            count += 1
        totals[key] = (count, size)
    return totals


def compare_files(backup_root: Path, live_root: Path) -> dict[str, Any]:
    """Files and bytes per first-level folder, backup next to live."""

    if not live_root.is_dir():
        raise StepFailed(f"the live folder {live_root} cannot be read from the host")
    backup, live = _walk(backup_root), _walk(live_root)
    folders: list[dict[str, Any]] = []
    for key in sorted(set(backup) | set(live)):
        b, v = backup.get(key, (0, 0)), live.get(key, (0, 0))
        folders.append({"folder": key, "files_backup": b[0], "files_live": v[0],
                        "bytes_backup": b[1], "bytes_live": v[1], "files_gap": v[0] - b[0]})
    folders.sort(key=lambda row: (-abs(int(row["files_gap"])), str(row["folder"])))
    return {
        "live_folder": str(live_root),
        "files_backup": sum(count for count, _ in backup.values()),
        "files_live": sum(count for count, _ in live.values()),
        "bytes_backup": sum(size for _, size in backup.values()),
        "bytes_live": sum(size for _, size in live.values()),
        "folders": folders,
    }


def live_mount_source(run: SandboxRun, container: str, destination: str) -> Path:
    """Where on the host the live container keeps `destination`."""

    shown = run.docker(
        "inspect", "--format", '{{range .Mounts}}{{.Destination}}|{{.Source}}{{"\\n"}}{{end}}', container
    ).stdout
    for line in shown.splitlines():
        target, _, source = line.partition("|")
        if target == destination and source:
            return Path(source)
    raise StepFailed(f"{container} mounts nothing at {destination}")


def compare(run: SandboxRun, parts: Iterable[tuple[str, Callable[[], dict[str, Any]]]]) -> None:
    """Run each comparison in one step; a part that cannot be compared
    is said in the report, the others still are."""

    if not run.compare:
        return
    with run.step("compare with live"):
        result: dict[str, Any] = {}
        for name, measure in parts:
            try:
                result[name] = measure()
            except StepFailed as error:
                result[name] = {"not_compared": str(error)}
        run.facts["comparison"] = result


def summary_lines(comparison: dict[str, Any]) -> list[str]:
    lines = ["Comparaison avec le service en marche (sauvegarde → vivant, sans verdict) :"]
    for name, part in comparison.items():
        if "not_compared" in part:
            lines.append(f"  {name} : non comparé — {part['not_compared']}")
        elif "tables" in part:
            lines.append(
                f"  {name} : {part['tables_compared']} table(s), {part['rows_backup']} → {part['rows_live']} ligne(s), "
                f"{part['tables_differing']} table(s) différente(s)"
            )
            for row in [row for row in part["tables"] if row["gap"]][:8]:
                lines.append(f"    {row['table']} : {row['backup']} → {row['live']} ({row['gap']:+d})")
            for label, key in (("seulement dans la sauvegarde", "only_in_backup"), ("seulement en vivant", "only_live")):
                if part[key]:
                    lines.append(f"    {label} : {', '.join(part[key])}")
        else:
            lines.append(
                f"  {name} : {part['files_backup']} → {part['files_live']} fichier(s), "
                f"{part['bytes_backup'] / 1024**2:.1f} → {part['bytes_live'] / 1024**2:.1f} Mo"
            )
            for row in [row for row in part["folders"] if row["files_gap"]][:8]:
                lines.append(f"    {row['folder']} : {row['files_backup']} → {row['files_live']} ({row['files_gap']:+d})")
    return lines
