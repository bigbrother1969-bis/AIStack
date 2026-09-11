from __future__ import annotations

from pathlib import Path

from aistack.contracts.gpu_threshold import GpuThreshold
from aistack.providers.gpu.yaml import load_gpu_thresholds_yaml


def gpu_thresholds_for_host(
    path: Path, hostname: str
) -> tuple[tuple[GpuThreshold, ...], str]:
    """
    Read `path`'s declared GPU thresholds for `hostname`, or an empty
    tuple with a note explaining why — never raises.

    Mirrors `storage_thresholds_for_host`/`backup_thresholds_for_host`
    exactly (same three branches, same message shape), and — like
    `backup_thresholds_for_host` — is imported directly by both
    `aistack.cli.runtime_diagnose` and `aistack.cli.health_render` from
    the start: neither carried GPU-checking code of its own before this
    domain existed, so there is no prior duplicate to preserve.
    """

    if not path.exists():
        return (), (
            f"no GPU-threshold definition at {path}; GPU consumption is "
            f"not checked"
        )

    try:
        register = load_gpu_thresholds_yaml(path)
    except (ValueError, OSError) as error:
        return (), (
            f"GPU-threshold definition not readable ({error}); GPU "
            f"consumption is not checked"
        )

    thresholds = register.for_host(hostname)

    if not thresholds:
        return (), (
            f"no GPU thresholds declared for host {hostname!r} in "
            f"{path}; GPU consumption is not checked"
        )

    return thresholds, ""
