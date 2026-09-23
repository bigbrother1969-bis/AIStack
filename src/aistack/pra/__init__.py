"""
PRA tests — `PLAN-J11` § 11.9.1's third and last named gap ("tests
PRA"), reopened and closed 2026-09-23
(`claude/PLAN-J11-CONSOLE-2026-09-11.md`,
`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` § 9).

Not a live observation surface: every fact a `PraTestReading` carries
is the owner's own declared record of a restore test performed by
hand (`GOV-P-001`) — `OPS-0009`'s YAML, `pra_tests.yml`, names both
which five services this domain checks and each one's own last-known
test outcome, the same "declared, not collected" split
`aistack.console`'s links already hold, not a provider reaching a
live system the way `StorageProvider`/`BackupProvider`/`NvidiaGpuProvider`
do — there is nothing live for one to reach.
"""

from aistack.pra.yaml.store import load_pra_tests_yaml

__all__ = ["load_pra_tests_yaml"]
