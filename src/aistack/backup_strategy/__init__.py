"""
Backup strategy — 1.6 tranche 2's own domain (R9, 2026-09-30):
confronting every stateful service already named in this session's
real PRA history against the backup mechanism (if any) actually known
to cover it.

Not a live observation surface, the same way `aistack.pra` is not:
every fact a `BackupStrategyDeclaration` carries is the owner's own
declared record, or an honest "not confirmed" where this session could
not ground one (`GOV-P-001`) — `OPS-0010`'s YAML,
`backup_strategy.yml`, names both which services this domain checks
and, for each, whether a real mechanism is known to cover its
persistent state.
"""

from aistack.backup_strategy.yaml import load_backup_strategy_yaml

__all__ = ["load_backup_strategy_yaml"]
