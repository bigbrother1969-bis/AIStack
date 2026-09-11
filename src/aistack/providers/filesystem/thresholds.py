from __future__ import annotations

from pathlib import Path

from aistack.contracts.storage_threshold import StorageThreshold
from aistack.providers.filesystem.yaml import load_storage_thresholds_yaml


def storage_thresholds_for_host(
    path: Path, hostname: str
) -> tuple[tuple[StorageThreshold, ...], str]:
    """
    Read `path`'s declared storage thresholds for `hostname`, or an
    empty tuple with a note explaining why — never raises.

    **Shared, so it is written once.** `aistack.cli.runtime_diagnose`
    already carries a function of this exact shape (same three
    branches, same messages) — this module does not replace it: no
    CLI in this package imports another (`architecture_render.py`
    composes `DockerRuntimeCatalogBuilder`/`ComposeRuntimeCatalogBuilder`
    directly rather than importing `docker_catalog.main`, the
    established boundary), so `runtime_diagnose.py` was left as it
    already stood, published and tested, rather than reshaped for a
    caller it did not yet have. `aistack.cli.health_render`
    (`PLAN-J7`, `claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`) is the
    second consumer, and lives next to `StorageProvider` — a module
    both CLIs already depend on — rather than duplicate the three
    messages a third time or reach into a CLI module for them.

    `hostname` narrows a fleet-wide file (GIGABYTE and the Raspberry
    both declared in the same `storage_thresholds.yml`) to the one
    host this process is actually running on — the caller passes
    `socket.gethostname()`, not a command-line flag, the same "this
    process only ever examines the host it runs on" scope
    `DockerProvider`/`HostProvider` already hold without being told
    which host that is.
    """

    if not path.exists():
        return (), (
            f"no storage-threshold definition at {path}; storage "
            f"capacity is not checked"
        )

    try:
        register = load_storage_thresholds_yaml(path)
    except (ValueError, OSError) as error:
        return (), (
            f"storage-threshold definition not readable ({error}); "
            f"storage capacity is not checked"
        )

    thresholds = register.for_host(hostname)

    if not thresholds:
        return (), (
            f"no storage thresholds declared for host {hostname!r} in "
            f"{path}; storage capacity is not checked"
        )

    return thresholds, ""
