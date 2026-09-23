from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CmdbProbeTargetDefinition:
    """
    One HTTP endpoint the "CMDB temps réel" section probes at render
    time — a name to display and the public URL to request.

    `claude/PLAN-J11-CONSOLE-2026-09-11.md` §11.9.1, first of the
    three gaps named 2026-09-13, scoped and built 2026-09-23. Loaded
    from `cmdb_probe_targets.yml`
    (`src/aistack/architecture/yaml/cmdb_targets_store.py`) — a
    hand-written list, the same governance stance
    `InfrastructureTopologyDefinition`/`ServiceCategorizationDefinition`
    already take: no provider observes which endpoints matter to the
    owner, that is his own decision (`GOV-P-001`).

    Deliberately a plain (name, url) pair and nothing more — unlike
    `BeszelConnectionDefinition`, there are no credentials to name
    here, only public URLs already declared elsewhere in this project
    (`service_categorization.yml`'s own `href` fields cover an
    overlapping, but not identical, set — see `cmdb_probe_targets.yml`'s
    own header comment for why this project keeps a separate list
    rather than deriving one from the other).
    """

    name: str
    url: str
