from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArrivalsDefinition:
    """
    What the owner declared about arrivals (`arrivals.yml`).

    `confirm_passes`: a container is said new once it was seen on that many
    vigil passes in a row (a pass is 15 minutes apart). `machine_scan_hours`:
    how often the vigil runs the network discovery (SSH attempts against
    every live host of the LAN); 0, the shipped value, never runs it — a scan
    is an action, so the owner switches it on. `ignore`: containers never
    proposed. `known_hosts`: addresses of machines that are not news.
    """

    confirm_passes: int = 2
    machine_scan_hours: float = 0.0
    ignore: tuple[str, ...] = ()
    known_hosts: tuple[str, ...] = ()
