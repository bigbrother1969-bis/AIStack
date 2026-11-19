"""
Is a declaration a file its own loader reads? (`ADR-0027` § 12).

Each declaration the package ships has a loader that says what it accepts and
raises when the file is not that. A file edited by hand is valid when its
loader reads it. Nothing is blocked and nothing is restored: an invalid file
is reported, with the last copy that was valid, and the owner decides.

`LOADERS` names every shipped declaration. A test fails when the package ships
one that is not named here, so a new declaration comes with its validation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from aistack.generators.history import write_artifact_with_history

from aistack.ai_runtime.yaml.store import load_ai_runtime_yaml
from aistack.api_keys import load_api_keys
from aistack.architecture.yaml.cmdb_targets_store import load_cmdb_probe_targets_yaml
from aistack.architecture.yaml.store import load_service_categorization_yaml
from aistack.architecture.yaml.topology_store import load_infrastructure_topology_yaml
from aistack.arrivals.load import load_arrivals_yaml
from aistack.authentication.definition import load_authentication_yaml
from aistack.backup_strategy.yaml.store import load_backup_strategy_yaml
from aistack.console.identity import load_console_identity
from aistack.console.yaml.store import load_console_links_yaml
from aistack.data_budget.budget import load_data_budget
from aistack.dock.declaration import load_dock_declaration
from aistack.health.yaml.store import load_health_score_weights_yaml
from aistack.hosts.records import load_hosts_declaration
from aistack.i18n.catalog import load_languages_yaml
from aistack.instance.yaml.store import load_instance_config_yaml
from aistack.network_discovery.yaml.store import load_network_discovery_yaml
from aistack.pra.yaml.store import load_pra_tests_yaml
from aistack.priority.yaml.store import load_resource_priority_yaml
from aistack.providers.filesystem.yaml.backup_store import load_backup_thresholds_yaml
from aistack.providers.filesystem.yaml.store import load_storage_thresholds_yaml
from aistack.providers.gpu.yaml.store import load_gpu_thresholds_yaml
from aistack.restart_watch.load import load_restart_watch_yaml
from aistack.sandbox.declaration import load_sandbox_declaration
from aistack.security.yaml import load_security_yaml
from aistack.sync.declaration import load_sync_declaration

# A loader reads the file at `path`; `generated` is for the one that also
# reads the data directory (`hosts.yml`).
Loader = Callable[[Path, Path], object]

LOADERS: dict[str, Loader] = {
    "ai_runtime.yml": lambda path, _: load_ai_runtime_yaml(path),
    "api_keys.yml": lambda path, _: load_api_keys(path),
    "arrivals.yml": lambda path, _: load_arrivals_yaml(path),
    "authentication.yml": lambda path, _: load_authentication_yaml(path),
    "backup_strategy.yml": lambda path, _: load_backup_strategy_yaml(path),
    "backup_thresholds.yml": lambda path, _: load_backup_thresholds_yaml(path),
    "cmdb_probe_targets.yml": lambda path, _: load_cmdb_probe_targets_yaml(path),
    "console_identity.yml": lambda path, _: load_console_identity(path),
    "console_links.yml": lambda path, _: load_console_links_yaml(path),
    "data_budget.yml": lambda path, _: load_data_budget(path),
    "dock.yml": lambda path, _: load_dock_declaration(path),
    "gpu_thresholds.yml": lambda path, _: load_gpu_thresholds_yaml(path),
    "health_score_weights.yml": lambda path, _: load_health_score_weights_yaml(path),
    "hosts.yml": lambda path, generated: load_hosts_declaration(generated, path),
    "infrastructure_topology.yml": lambda path, _: load_infrastructure_topology_yaml(path),
    "instance_config.yml": lambda path, _: load_instance_config_yaml(path),
    "languages.yml": lambda path, _: load_languages_yaml(path),
    "network_discovery.yml": lambda path, _: load_network_discovery_yaml(path),
    "pra_tests.yml": lambda path, _: load_pra_tests_yaml(path),
    "resource_priority.yml": lambda path, _: load_resource_priority_yaml(path),
    "restart_watch.yml": lambda path, _: load_restart_watch_yaml(path),
    "sandbox.yml": lambda path, _: load_sandbox_declaration(path),
    "security.yml": lambda path, _: load_security_yaml(path),
    "service_categorization.yml": lambda path, _: load_service_categorization_yaml(path),
    "storage_thresholds.yml": lambda path, _: load_storage_thresholds_yaml(path),
    "sync.yml": lambda path, _: load_sync_declaration(path),
}

MAX_ERROR = 300
# What is invalid now, one file in the data directory (with its history): the
# vigil says it once, Settings shows it. Names, loader's words and copies only.
STATE = "declaration-invalid.json"


@dataclass(frozen=True)
class Invalid:
    """A declaration its loader does not read, and what it said. Never the content."""

    name: str
    error: str


def problem(name: str, path: Path, generated: Path) -> str:
    """
    Why the file at `path` is not read by the loader of the shipped
    declaration `name`; `""` when it is (or when `name` is not a declaration).
    """

    loader = LOADERS.get(name)

    if loader is None:
        return ""

    try:
        loader(path, generated)

    except yaml.MarkedYAMLError as error:
        mark = error.problem_mark
        where = f" (line {mark.line + 1}, column {mark.column + 1})" if mark is not None else ""
        return _short(f"{error.problem or 'not YAML'}{where}")

    except Exception as error:  # a loader may raise anything about a file it cannot read
        return _short(f"{type(error).__name__}: {error}")

    return ""


def validate(config_dir: Path, generated: Path, shipped: list[Path]) -> list[Invalid]:
    """The declarations of `config_dir` that their loader does not read. Writes nothing."""

    invalid: list[Invalid] = []

    for source in shipped:
        current = config_dir / source.name

        if not current.is_file():
            continue

        why = problem(source.name, current, generated)

        if why:
            invalid.append(Invalid(source.name, why))

    return invalid


def last_valid_copy(generated: Path, name: str, seen: Path) -> str:
    """
    The newest copy kept by the observation (`<name>.avant-observe-*` under
    `seen`) that the loader of `name` reads; `""` when none is.
    """

    for copy in sorted(seen.glob(f"{name}.avant-observe-*"), reverse=True):
        if not problem(name, copy, generated):
            return str(copy)

    return ""


def _short(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= MAX_ERROR else text[: MAX_ERROR - 1] + "…"


def record_invalid(generated: Path, invalid: list[Invalid], seen_of: Callable[[str], Path]) -> list[dict[str, str]]:
    """
    Keep what is invalid now, written every pass so that "valid again" is also
    known (an empty list). The file carries no time: an unchanged state adds
    nothing to its history. Returns the entries.
    """

    entries = [
        {"name": item.name, "error": item.error, "last_valid_copy": last_valid_copy(generated, item.name, seen_of(item.name))}
        for item in sorted(invalid, key=lambda item: item.name)
    ]
    write_artifact_with_history(json.dumps({"invalid": entries}, ensure_ascii=False, indent=1) + "\n", generated / STATE)
    return entries


def read_invalid(generated: Path) -> list[dict[str, str]]:
    """What `record_invalid` kept; empty when there is nothing or the file is unreadable."""

    try:
        data = json.loads((generated / STATE).read_text(encoding="utf-8"))
        return [
            {key: str(item.get(key, "")) for key in ("name", "error", "last_valid_copy")}
            for item in data["invalid"]
            if isinstance(item, dict)
        ]
    except (OSError, ValueError, KeyError, TypeError):
        return []
