from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class Probe:
    """
    A check for a container that declares no healthcheck of its own.

    `url` is asked from the host's network (the watcher runs on it). Any
    HTTP answer under 500 counts as alive: the probe asks whether the
    program answers at all, never whether it is right.
    """

    url: str
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class RestartWatchDefinition:
    """
    What the watch is allowed to do, as the owner declared it.

    `after` is the exception to the order read from Docker: `after:
    {firefly: [firefly_db]}` restarts `firefly_db` first. `never` lists
    containers left alone however they look. `probes` gives a container
    without a healthcheck a way to be judged stuck.
    """

    window_minutes: int = 30
    poll_seconds: float = 30.0
    confirm_cycles: int = 2
    max_attempts_per_hour: int = 2
    wait_seconds: float = 180.0
    after: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: MappingProxyType({}))
    never: tuple[str, ...] = ()
    probes: Mapping[str, Probe] = field(default_factory=lambda: MappingProxyType({}))
