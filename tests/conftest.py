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

import os
from pathlib import Path

# The reference host's declarations (2.0.0-rc1): the package ships
# neutral ones, and the suite reads GIGABYTE's, as it always has, from
# tests/reference/definitions — set before anything imports aistack,
# since a module resolves its declaration's path when it is imported.
REFERENCE_DEFINITIONS = Path(__file__).resolve().parent / "reference" / "definitions"
os.environ["AISTACK_REFERENCE_DIR"] = str(REFERENCE_DEFINITIONS)

import pytest  # noqa: E402

from aistack.health.cockpit import HealthDomain  # noqa: E402

_COCKPIT_BUILDERS = (
    "aistack.cli.health_render",
    "aistack.cli.console_render",
    "aistack.troubleshooting.findings",
)


@pytest.fixture(autouse=True)
def _quiet_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    def quiet(*_args: object, **_kwargs: object) -> HealthDomain:
        return HealthDomain(name="Hôtes", instrumented=True)

    def quiet_data(*_args: object, **_kwargs: object) -> HealthDomain:
        return HealthDomain(name="Données d'AIStack", instrumented=True)

    for module in _COCKPIT_BUILDERS:
        monkeypatch.setattr(f"{module}.hosts_domain", quiet)
        # AIStack's data directory against its budget (2.0, ADR-0021):
        # the real one is measured by tests/unit/data_budget.
        monkeypatch.setattr(f"{module}.data_budget_domain", quiet_data)
        # The scheduled restore tests' records (2.0) live in the real
        # data directory too: a cockpit built by a test reads
        # pra_tests.yml alone. `tests/unit/pra/test_scheduled.py` tests
        # the merge itself.
        monkeypatch.setattr(f"{module}.with_scheduled", lambda readings, *_args: tuple(readings))
