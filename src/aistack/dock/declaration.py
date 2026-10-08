"""
`dock.yml` (`ADR-0019` § 1): the services only the dock may update, the
sandbox recipe that rehearses each, and the live containers it may
recreate. Written by hand, read-only: a missing key is named.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from aistack.config import configured

SHIPPED = Path(__file__).resolve().parent / "definitions" / "dock.yml"


@dataclass(frozen=True)
class GovernedService:
    name: str
    recipe: str
    containers: tuple[str, ...]


def load_dock_declaration(path: Path | None = None) -> tuple[GovernedService, ...]:
    source = path if path is not None else configured(SHIPPED)
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{source}: not a mapping")
    services = []
    for name, raw in (data.get("services") or {}).items():
        where = f"{source}: service `{name}`"
        if not isinstance(raw, dict):
            raise ValueError(f"{where}: not a mapping")
        recipe = raw.get("recipe")
        containers = raw.get("containers")
        if not recipe:
            raise ValueError(f"{where}: `recipe` is missing")
        if not isinstance(containers, list) or not containers:
            raise ValueError(f"{where}: `containers` must list at least one container")
        services.append(GovernedService(str(name), str(recipe), tuple(str(item) for item in containers)))
    return tuple(services)
