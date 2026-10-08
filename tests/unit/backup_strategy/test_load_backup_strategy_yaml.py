from pathlib import Path

import pytest

from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.contracts.backup_strategy_declaration import (
    DUMP_SQL,
    LIVE_FILE_BACKUP,
    STOP_AND_ARCHIVE,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "backup_strategy.yml",
        """
        services:
          - name: wordpress
            host: GIGABYTE
            has_state: true
            engines: [dump_sql]
            mechanism: backup-wordpress.sh
          - name: nextcloud
            host: GIGABYTE
            has_state: true
            engines: []
            mechanism: null
        """,
    )

    declarations = load_backup_strategy_yaml(path)

    assert len(declarations) == 2

    by_service = {d.service: d for d in declarations}
    assert by_service["wordpress"].host == "GIGABYTE"
    assert by_service["wordpress"].engines == (DUMP_SQL,)
    assert by_service["wordpress"].mechanism == "backup-wordpress.sh"
    assert by_service["nextcloud"].engines == ()
    assert by_service["nextcloud"].mechanism is None
    assert by_service["nextcloud"].covered is False


def test_engines_may_be_omitted_entirely(tmp_path: Path):
    path = write(
        tmp_path / "backup_strategy.yml",
        """
        services:
          - name: gigabyte
            host: GIGABYTE
            has_state: true
        """,
    )

    declarations = load_backup_strategy_yaml(path)

    assert declarations[0].engines == ()


def test_a_definition_missing_services_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "not_services: []\n")

    with pytest.raises(ValueError, match="missing: services"):
        load_backup_strategy_yaml(path)


def test_services_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "services: not-a-list\n")

    with pytest.raises(ValueError, match="must be a list"):
        load_backup_strategy_yaml(path)


def test_a_service_entry_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "services:\n  - just-a-string\n")

    with pytest.raises(ValueError, match="must be a mapping"):
        load_backup_strategy_yaml(path)


def test_a_service_entry_missing_name_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml", "services:\n  - host: GIGABYTE\n    has_state: true\n"
    )

    with pytest.raises(ValueError, match="missing: name"):
        load_backup_strategy_yaml(path)


def test_a_service_entry_missing_host_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "services:\n  - name: wordpress\n    has_state: true\n",
    )

    with pytest.raises(ValueError, match="missing: host"):
        load_backup_strategy_yaml(path)


def test_a_service_entry_missing_has_state_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "services:\n  - name: wordpress\n    host: GIGABYTE\n",
    )

    with pytest.raises(ValueError, match="missing: has_state"):
        load_backup_strategy_yaml(path)


def test_engines_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        (
            "services:\n  - name: wordpress\n    host: GIGABYTE\n"
            "    has_state: true\n    engines: dump_sql\n"
            "    mechanism: backup-wordpress.sh\n"
        ),
    )

    with pytest.raises(ValueError, match="engines must be a list"):
        load_backup_strategy_yaml(path)


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_backup_strategy_yaml(path)


def test_invalid_yaml_syntax_is_reported_as_a_value_error(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "services: [not, valid,\n")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_backup_strategy_yaml(path)


def test_the_real_backup_strategy_definition_loads():
    """
    `src/aistack/backup_strategy/definitions/backup_strategy.yml` is
    not a fixture — it is `OPS-0010`'s own declared v1 scope, the file
    `aistack.cli.health_render`/`aistack.cli.console_render` actually
    read. Loading it here means a typo in the real, hand-written file
    is caught by the test suite, the same discipline
    `test_the_real_pra_tests_definition_loads` already holds.
    """

    repo_root = Path(__file__).resolve().parents[3]

    declarations = load_backup_strategy_yaml(
        repo_root
        / "src"
        / "aistack"
        / "backup_strategy"
        / "definitions"
        / "backup_strategy.yml"
    )

    by_service = {d.service: d for d in declarations}
    assert set(by_service) == {
        "wordpress",
        "arrstack",
        "nextcloud",
        "nextcloud-files",
        "immich",
        "immich-uploads",
        "gigabyte",
        "changedetection",
        "homepage",
        "npm",
        "pocketid",
        "uptime-kuma",
        "vaultwarden",
        "vikunja",
        "aistack",
    }

    assert by_service["aistack"].engines == (DUMP_SQL, LIVE_FILE_BACKUP)
    assert by_service["wordpress"].engines == (DUMP_SQL,)
    assert by_service["arrstack"].engines == (STOP_AND_ARCHIVE,)
    assert by_service["changedetection"].engines == (LIVE_FILE_BACKUP,)
    assert by_service["vikunja"].engines == (DUMP_SQL, LIVE_FILE_BACKUP)

    # 1.6 closure, 2026-10-02: the three real gaps found 2026-09-30
    # grounded — systemd timers (dump_sql) + Deja Dup (live_file_backup,
    # owner-stated) for nextcloud/immich, Clonezilla (stop_and_archive,
    # owner-stated) for the gigabyte host itself.
    #
    # Corrected 2026-10-08 (1.9 sandbox cadrage): Nextcloud's files and
    # Immich's uploads live on the backup disk itself and Deja Dup does
    # not copy them — two stateful parts no engine covers, stated as
    # such. Only Immich's external library is really copied.
    assert by_service["nextcloud"].engines == (DUMP_SQL,)
    assert by_service["immich"].engines == (DUMP_SQL, LIVE_FILE_BACKUP)
    assert by_service["gigabyte"].engines == (STOP_AND_ARCHIVE,)
    assert by_service["nextcloud"].covered is True
    assert by_service["immich"].covered is True
    assert by_service["gigabyte"].covered is True
    assert by_service["nextcloud-files"].covered is False
    assert by_service["immich-uploads"].covered is False

    for declaration in declarations:
        assert declaration.has_state is True
