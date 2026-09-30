import pytest

from aistack.contracts.backup_strategy_declaration import (
    DUMP_SQL,
    BackupStrategyDeclaration,
)
from aistack.contracts.uncovered_state_gap import UncoveredStateGap


def test_a_stateless_declaration_is_refused():
    declaration = BackupStrategyDeclaration(
        service="it-tools", host="GIGABYTE", has_state=False
    )

    with pytest.raises(ValueError, match="declares no persistent state"):
        UncoveredStateGap(declaration=declaration)


def test_a_covered_declaration_is_refused():
    declaration = BackupStrategyDeclaration(
        service="wordpress",
        host="GIGABYTE",
        has_state=True,
        engines=(DUMP_SQL,),
        mechanism="backup-wordpress.sh",
    )

    with pytest.raises(ValueError, match="already covered"):
        UncoveredStateGap(declaration=declaration)


def test_an_uncovered_stateful_declaration_is_accepted():
    declaration = BackupStrategyDeclaration(
        service="nextcloud", host="GIGABYTE", has_state=True
    )

    gap = UncoveredStateGap(declaration=declaration)

    assert gap.declaration is declaration
