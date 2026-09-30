from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.backup_strategy_declaration import BackupStrategyDeclaration

_REQUIRED_SERVICE_FIELDS = ("name", "host", "has_state")


def load_backup_strategy_yaml(path: Path) -> tuple[BackupStrategyDeclaration, ...]:
    """
    Load `OPS-0010`'s declared backup-strategy records from YAML:
    every service this domain checks, whether it holds persistent
    state, and which real backup engine(s) (if any are confirmed)
    cover it.

    Mirrors `load_pra_tests_yaml` field for field (written by hand,
    read-only — every value here is the owner's own declared record,
    or an explicit "not confirmed" where this session could not
    ground one — so a missing required key is a typo, and the error
    names which one and where; nothing writes this file back).
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            raise ValueError(
                f"Backup strategy definition {path} is not valid YAML: {error}"
            ) from error

    if not isinstance(data, dict):
        raise ValueError(f"Backup strategy definition must contain a mapping: {path}")

    if "services" not in data:
        raise ValueError(f"Backup strategy definition {path} is missing: services")

    services_data = data["services"]

    if not isinstance(services_data, list):
        raise ValueError(f"Backup strategy definition {path}: services must be a list")

    return tuple(
        _load_service(item, path, index) for index, item in enumerate(services_data)
    )


def _load_service(
    data: Any, path: Path, index: int
) -> BackupStrategyDeclaration:
    label = f"Backup strategy definition {path}: services[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_SERVICE_FIELDS, label)

    engines_data = data.get("engines") or []

    if not isinstance(engines_data, list):
        raise ValueError(f"{label}.engines must be a list, or omitted")

    return BackupStrategyDeclaration(
        service=data["name"],
        host=data["host"],
        has_state=bool(data["has_state"]),
        engines=tuple(str(engine) for engine in engines_data),
        mechanism=data.get("mechanism"),
    )


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
