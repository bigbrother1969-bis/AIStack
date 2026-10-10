from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.backup_strategy_declaration import BackupStrategyDeclaration
from aistack.contracts.uncovered_state_gap import UncoveredStateGap


def find_uncovered_state(
    declarations: Sequence[BackupStrategyDeclaration],
) -> tuple[UncoveredStateGap, ...]:
    """
    Return the declared services that hold persistent state with no backup
    engine covering it (`OPS-0010`, R9). A stateless declaration is never a gap.
    """

    return tuple(
        UncoveredStateGap(declaration=declaration)
        for declaration in declarations
        if declaration.has_state and not declaration.covered
    )
