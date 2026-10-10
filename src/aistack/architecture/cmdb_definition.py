from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CmdbProbeTargetDefinition:
    """
    One HTTP endpoint the "CMDB temps réel" section probes at render time:
    a display name and a public URL. Loaded from `cmdb_probe_targets.yml`.
    """

    name: str
    url: str
