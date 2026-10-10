"""
Backup strategy: for each declared stateful service, the backup mechanism
known to cover it, if any.

Declared, not observed: `backup_strategy.yml` (`OPS-0010`) lists the
services checked and, for each, the confirmed backup engines or none.
"""

from aistack.backup_strategy.yaml import load_backup_strategy_yaml

__all__ = ["load_backup_strategy_yaml"]
