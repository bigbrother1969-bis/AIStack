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

KINDS = ("wordpress_mariadb",)


@dataclass(frozen=True)
class SandboxRecipe:
    name: str
    kind: str
    backup_dir: Path
    database_dump: str
    files_archive: str
    live_database_container: str
    live_web_container: str
    database_timeout_seconds: float = 900
    web_timeout_seconds: float = 180


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
        recipes[str(name)] = SandboxRecipe(
            name=str(name),
            kind=str(kind),
            backup_dir=Path(str(_required(raw, "backup_dir", where))),
            database_dump=str(_required(raw, "database_dump", where)),
            files_archive=str(_required(raw, "files_archive", where)),
            live_database_container=str(_required(raw, "live_database_container", where)),
            live_web_container=str(_required(raw, "live_web_container", where)),
            database_timeout_seconds=float(raw.get("database_timeout_seconds", 900)),
            web_timeout_seconds=float(raw.get("web_timeout_seconds", 180)),
        )

    return SandboxDeclaration(
        run_root=Path(str(_required(data, "run_root", str(source)))),
        margin_gib=float(data.get("margin_gib", 1)),
        expansion=float(data.get("expansion", 4)),
        recipes=recipes,
    )
