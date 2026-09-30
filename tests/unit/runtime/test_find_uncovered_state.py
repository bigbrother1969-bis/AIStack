from aistack.contracts.backup_strategy_declaration import (
    DUMP_SQL,
    BackupStrategyDeclaration,
)
from aistack.runtime.uncovered_state_gap import find_uncovered_state


def covered(service: str) -> BackupStrategyDeclaration:
    return BackupStrategyDeclaration(
        service=service,
        host="GIGABYTE",
        has_state=True,
        engines=(DUMP_SQL,),
        mechanism="a real script",
    )


def uncovered(service: str) -> BackupStrategyDeclaration:
    return BackupStrategyDeclaration(service=service, host="GIGABYTE", has_state=True)


def stateless(service: str) -> BackupStrategyDeclaration:
    return BackupStrategyDeclaration(service=service, host="GIGABYTE", has_state=False)


def test_a_covered_stateful_service_is_not_flagged():
    gaps = find_uncovered_state([covered("wordpress")])

    assert gaps == ()


def test_an_uncovered_stateful_service_is_flagged():
    gaps = find_uncovered_state([uncovered("nextcloud")])

    assert len(gaps) == 1
    assert gaps[0].declaration.service == "nextcloud"


def test_a_stateless_service_is_never_flagged():
    gaps = find_uncovered_state([stateless("it-tools")])

    assert gaps == ()


def test_only_the_uncovered_services_are_flagged_in_a_batch():
    gaps = find_uncovered_state(
        [covered("wordpress"), uncovered("nextcloud"), stateless("it-tools")]
    )

    assert [gap.declaration.service for gap in gaps] == ["nextcloud"]


def test_an_empty_declaration_set_flags_nothing():
    assert find_uncovered_state([]) == ()
