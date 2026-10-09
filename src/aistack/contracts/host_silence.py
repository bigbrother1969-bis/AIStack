"""
A traced host whose collector has stopped writing (`ADR-0020`; 2.0,
the owner, 2026-10-09: "hôte silencieux = constat Santé").
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HostSilence:
    """
    One host `hosts.yml` traces and nothing recent was read from.

    `minutes` is how long since its collector's last run; `None` when
    no run was read at all — no `host.json`, an unreadable one, or the
    disk that holds it not mounted (`problem` then says which).
    """

    host: str
    directory: str
    last_run: str = ""
    minutes: int | None = None
    problem: str = ""

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("a host silence names no host")
        if self.minutes is None and not self.problem.strip():
            raise ValueError(f"{self.host}: no run read, and no reason given")
