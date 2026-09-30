import pytest

from aistack.contracts.backup_strategy_declaration import (
    DUMP_SQL,
    LIVE_FILE_BACKUP,
    STOP_AND_ARCHIVE,
    BackupStrategyDeclaration,
)


def test_a_declaration_names_no_service_is_refused():
    with pytest.raises(ValueError, match="names no service"):
        BackupStrategyDeclaration(service="", host="GIGABYTE", has_state=True)


def test_a_declaration_names_no_host_is_refused():
    with pytest.raises(ValueError, match="declares no host"):
        BackupStrategyDeclaration(service="wordpress", host="", has_state=True)


def test_an_unknown_engine_is_refused():
    with pytest.raises(ValueError, match="unknown engine"):
        BackupStrategyDeclaration(
            service="wordpress",
            host="GIGABYTE",
            has_state=True,
            engines=("full_disk_image",),
            mechanism="Clonezilla",
        )


def test_a_repeated_engine_is_refused():
    with pytest.raises(ValueError, match="more than once"):
        BackupStrategyDeclaration(
            service="wordpress",
            host="GIGABYTE",
            has_state=True,
            engines=(DUMP_SQL, DUMP_SQL),
            mechanism="mysqldump twice, somehow",
        )


def test_a_stateless_service_naming_an_engine_is_refused():
    with pytest.raises(ValueError, match="no persistent state but names"):
        BackupStrategyDeclaration(
            service="it-tools",
            host="GIGABYTE",
            has_state=False,
            engines=(DUMP_SQL,),
            mechanism="not applicable",
        )


def test_engines_declared_with_no_mechanism_is_refused():
    with pytest.raises(ValueError, match="no mechanism describing them"):
        BackupStrategyDeclaration(
            service="wordpress", host="GIGABYTE", has_state=True, engines=(DUMP_SQL,)
        )


def test_a_blank_mechanism_is_refused():
    with pytest.raises(ValueError, match="blank mechanism"):
        BackupStrategyDeclaration(
            service="wordpress",
            host="GIGABYTE",
            has_state=True,
            engines=(DUMP_SQL,),
            mechanism="   ",
        )


def test_a_stateless_service_with_no_engines_is_accepted():
    declaration = BackupStrategyDeclaration(
        service="it-tools", host="GIGABYTE", has_state=False
    )

    assert declaration.covered is False


def test_a_stateful_service_with_no_engines_is_uncovered():
    declaration = BackupStrategyDeclaration(
        service="nextcloud", host="GIGABYTE", has_state=True
    )

    assert declaration.covered is False


def test_a_stateful_service_with_an_engine_is_covered():
    declaration = BackupStrategyDeclaration(
        service="arrstack",
        host="GIGABYTE",
        has_state=True,
        engines=(STOP_AND_ARCHIVE,),
        mechanism="backup-arrstack.sh",
    )

    assert declaration.covered is True


def test_a_declaration_may_name_more_than_one_engine():
    """Vikunja's own real mechanism: a MariaDB dump for its database,
    a live restic snapshot for its files."""

    declaration = BackupStrategyDeclaration(
        service="vikunja",
        host="raspberry",
        has_state=True,
        engines=(DUMP_SQL, LIVE_FILE_BACKUP),
        mechanism="mariadb-dump + restic",
    )

    assert declaration.covered is True
    assert declaration.engines == (DUMP_SQL, LIVE_FILE_BACKUP)
