from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.backup_strategy_declaration import BackupStrategyDeclaration
from aistack.contracts.uncovered_state_gap import UncoveredStateGap


def find_uncovered_state(
    declarations: Sequence[BackupStrategyDeclaration],
) -> tuple[UncoveredStateGap, ...]:
    """
    Which declared services hold persistent state with no known
    backup engine covering it — `OPS-0010`'s own "état persistant non
    couvert" constat (R9).

    Mirrors `find_pra_test_gaps`/`find_backup_gaps`: given
    declarations already loaded, decides which ones actually fail —
    it never proposes a declaration itself. A stateless declaration
    (`has_state=False`) is never a gap, whether or not it names
    engines (`BackupStrategyDeclaration.__post_init__` already
    forbids a stateless service from naming any).

    Pure: declarations already loaded in, gaps out — the same
    discipline `find_pra_test_gaps`/`find_backup_gaps` already hold.
    """

    return tuple(
        UncoveredStateGap(declaration=declaration)
        for declaration in declarations
        if declaration.has_state and not declaration.covered
    )
