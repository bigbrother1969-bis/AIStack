"""
`sandbox.yml` (`ADR-0018` § 3–4): where sandboxes are restored, how
much room they need, and one recipe per service.

Written by hand, read-only: a missing or mistyped key is an error that
names it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aistack.config import configured

SHIPPED = Path(__file__).resolve().parent / "definitions" / "sandbox.yml"

KINDS = ("wordpress_mariadb", "aistack_archive", "nextcloud_mariadb", "immich_postgres")

# What each kind needs beyond `backup_dir`.
_NEEDS = {
    "wordpress_mariadb": ("database_dump", "files_archive", "live_database_container", "live_web_container"),
    "aistack_archive": ("files_archive", "live_web_container"),
    "nextcloud_mariadb": ("database_dump", "live_database_container"),
    "immich_postgres": ("database_dump", "live_database_container"),
}


@dataclass(frozen=True)
class FileSample:
    """A few files the restored database names, taken back from a
    Deja Dup (duplicity) backup and compared with what the database
    says of them (`ADR-0018` § 4, owner's choice 2026-10-08)."""

    live_prefix: str
    host_prefix: str
    duplicity_target: Path
    count: int = 3
    older_than_days: int = 8


@dataclass(frozen=True)
class SandboxRecipe:
    name: str
    kind: str
    backup_dir: Path
    files_archive: str = ""
    live_web_container: str = ""
    database_dump: str = ""
    live_database_container: str = ""
    database_timeout_seconds: float = 900
    web_timeout_seconds: float = 180
    # Overrides the declaration-wide factor (a database grows more than
    # an archive once loaded and indexed).
    expansion: float | None = None
    file_sample: FileSample | None = None
    # What of the service's state no backup holds, said in the report.
    not_backed_up: str = ""


@dataclass(frozen=True)
class SandboxDeclaration:
    run_root: Path
    margin_gib: float
    expansion: float
    recipes: dict[str, SandboxRecipe]


def _required(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data or data[key] in (None, ""):
        raise ValueError(f"{where}: `{key}` is missing")
    return data[key]


def load_sandbox_declaration(path: Path | None = None) -> SandboxDeclaration:
    source = path if path is not None else configured(SHIPPED)
    with source.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{source}: not a mapping")

    recipes: dict[str, SandboxRecipe] = {}
    for name, raw in (data.get("recipes") or {}).items():
        where = f"{source}: recipe `{name}`"
        if not isinstance(raw, dict):
            raise ValueError(f"{where}: not a mapping")
        kind = _required(raw, "kind", where)
        if kind not in KINDS:
            raise ValueError(f"{where}: unknown kind `{kind}` (known: {', '.join(KINDS)})")
        for key in _NEEDS[str(kind)]:
            _required(raw, key, where)
        sample = raw.get("file_sample")
        file_sample = None
        if sample is not None:
            if not isinstance(sample, dict):
                raise ValueError(f"{where}: `file_sample` is not a mapping")
            file_sample = FileSample(
                live_prefix=str(_required(sample, "live_prefix", f"{where} file_sample")),
                host_prefix=str(_required(sample, "host_prefix", f"{where} file_sample")),
                duplicity_target=Path(str(_required(sample, "duplicity_target", f"{where} file_sample"))),
                count=int(sample.get("count", 3)),
                older_than_days=int(sample.get("older_than_days", 8)),
            )
        recipes[str(name)] = SandboxRecipe(
            name=str(name),
            kind=str(kind),
            backup_dir=Path(str(_required(raw, "backup_dir", where))),
            files_archive=str(raw.get("files_archive") or ""),
            live_web_container=str(raw.get("live_web_container") or ""),
            database_dump=str(raw.get("database_dump") or ""),
            live_database_container=str(raw.get("live_database_container") or ""),
            database_timeout_seconds=float(raw.get("database_timeout_seconds", 900)),
            web_timeout_seconds=float(raw.get("web_timeout_seconds", 180)),
            expansion=float(raw["expansion"]) if raw.get("expansion") is not None else None,
            file_sample=file_sample,
            not_backed_up=str(raw.get("not_backed_up") or "").strip(),
        )

    return SandboxDeclaration(
        run_root=Path(str(_required(data, "run_root", str(source)))),
        margin_gib=float(data.get("margin_gib", 1)),
        expansion=float(data.get("expansion", 4)),
        recipes=recipes,
    )
