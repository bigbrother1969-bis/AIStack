"""
Suite-wide isolation.

Since 2.0 (2026-10-09) the health cockpit's Hosts domain reads the
records the host collectors write — on GIGABYTE, the real ones,
including the Raspberry's on /media/BACKUP. A test that builds the
cockpit must not depend on whether a real collector ran in the last
hour (the same lesson as 1.11's patch 0208 for the Time Machine
rebuild), so the three places that build it get a Hosts domain with
nothing to report. `tests/unit/hosts/test_hosts_health.py` tests the
real one, from `aistack.hosts.health` directly.
"""

from __future__ import annotations

import pytest

from aistack.health.cockpit import HealthDomain

_COCKPIT_BUILDERS = (
    "aistack.cli.health_render",
    "aistack.cli.console_render",
    "aistack.troubleshooting.findings",
)


@pytest.fixture(autouse=True)
def _quiet_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    def quiet(*_args: object, **_kwargs: object) -> HealthDomain:
        return HealthDomain(name="Hôtes", instrumented=True)

    for module in _COCKPIT_BUILDERS:
        monkeypatch.setattr(f"{module}.hosts_domain", quiet)
