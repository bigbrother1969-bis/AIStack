from pathlib import Path

import pytest

from aistack.contracts.storage_threshold import FREE_BYTES, PERCENT_USED
from aistack.providers.filesystem.yaml import load_storage_thresholds_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "storage_thresholds.yml",
        """
        hosts:
          - host: gigabyte
            thresholds:
              - mount: /
                kind: free_bytes
                free_gb: 20
              - mount: /media/Films
                kind: percent_used
                percent_used: 90
          - host: raspberry
            thresholds:
              - mount: /
                kind: free_bytes
                free_gb: 2
        """,
    )

    register = load_storage_thresholds_yaml(path)

    assert len(register.hosts) == 2
    gigabyte, raspberry = register.hosts

    assert gigabyte.host == "gigabyte"
    assert len(gigabyte.thresholds) == 2

    root, films = gigabyte.thresholds
    assert root.mount == "/"
    assert root.kind == FREE_BYTES
    assert root.value == 20 * 1024**3

    assert films.mount == "/media/Films"
    assert films.kind == PERCENT_USED
    assert films.value == 90.0

    assert raspberry.host == "raspberry"
    assert raspberry.thresholds[0].value == 2 * 1024**3


def test_a_host_with_no_thresholds_yet_is_valid(tmp_path: Path):
    path = write(
        tmp_path / "no_thresholds.yml",
        """
        hosts:
          - host: gigabyte
            thresholds: []
        """,
    )

    register = load_storage_thresholds_yaml(path)

    assert register.hosts[0].thresholds == ()


def test_a_definition_with_no_hosts_is_valid(tmp_path: Path):
    path = write(tmp_path / "no_hosts.yml", "hosts: []\n")

    assert load_storage_thresholds_yaml(path).hosts == ()


def test_a_missing_hosts_key_is_named(tmp_path: Path):
    path = write(tmp_path / "no_key.yml", "not_hosts: []\n")

    with pytest.raises(ValueError, match="missing: hosts"):
        load_storage_thresholds_yaml(path)


def test_hosts_that_are_not_a_list_are_refused(tmp_path: Path):
    path = write(tmp_path / "not_a_list.yml", "hosts: gigabyte\n")

    with pytest.raises(ValueError, match="hosts must be a list"):
        load_storage_thresholds_yaml(path)


def test_a_host_missing_its_own_required_field_is_named(tmp_path: Path):
    path = write(
        tmp_path / "bad_host.yml",
        """
        hosts:
          - thresholds: []
        """,
    )

    with pytest.raises(ValueError, match=r"hosts\[0\].*host"):
        load_storage_thresholds_yaml(path)


def test_a_hosts_thresholds_that_are_not_a_list_are_refused(tmp_path: Path):
    path = write(
        tmp_path / "not_a_list_thresholds.yml",
        """
        hosts:
          - host: gigabyte
            thresholds: /
        """,
    )

    with pytest.raises(ValueError, match="thresholds must be a list"):
        load_storage_thresholds_yaml(path)


def test_a_threshold_missing_its_kind_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_kind.yml",
        """
        hosts:
          - host: gigabyte
            thresholds:
              - mount: /
                free_gb: 20
        """,
    )

    with pytest.raises(ValueError, match=r"hosts\[0\]\.thresholds\[0\].*kind"):
        load_storage_thresholds_yaml(path)


def test_a_threshold_with_an_unknown_kind_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "unknown_kind.yml",
        """
        hosts:
          - host: gigabyte
            thresholds:
              - mount: /
                kind: percent_free
                free_gb: 20
        """,
    )

    with pytest.raises(ValueError, match="unknown threshold kind"):
        load_storage_thresholds_yaml(path)


def test_a_free_bytes_threshold_missing_free_gb_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_free_gb.yml",
        """
        hosts:
          - host: gigabyte
            thresholds:
              - mount: /
                kind: free_bytes
        """,
    )

    with pytest.raises(ValueError, match=r"thresholds\[0\].*free_gb"):
        load_storage_thresholds_yaml(path)


def test_a_percent_used_threshold_missing_percent_used_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_percent_used.yml",
        """
        hosts:
          - host: gigabyte
            thresholds:
              - mount: /media/Films
                kind: percent_used
        """,
    )

    with pytest.raises(ValueError, match=r"thresholds\[0\].*percent_used"):
        load_storage_thresholds_yaml(path)


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_storage_thresholds_yaml(path)


def test_the_real_storage_thresholds_definition_loads():
    """
    `src/aistack/providers/filesystem/definitions/storage_thresholds.yml`
    is not a fixture — it is `OPS-0005`'s own declared values, read
    live from `df -h` on GIGABYTE and the Raspberry, the file
    `aistack.cli.runtime_diagnose` actually reads. Loading it here
    means a typo in the real, hand-written file is caught by the test
    suite, the same discipline
    `test_the_real_resource_priority_definition_loads` already holds
    for `resource_priority.yml`.

    `host:` is asserted against the exact strings `hostname` printed
    on each machine (`GIGABYTE`, `raspberry`) — confirmed live by the
    owner, not guessed from either machine's role.
    """

    repo_root = Path(__file__).resolve().parents[4]

    register = load_storage_thresholds_yaml(
        repo_root
        / "src"
        / "aistack"
        / "providers"
        / "filesystem"
        / "definitions"
        / "storage_thresholds.yml"
    )

    gigabyte = register.for_host("GIGABYTE")
    raspberry = register.for_host("raspberry")

    assert len(gigabyte) == 7
    gigabyte_root = next(t for t in gigabyte if t.mount == "/")
    assert gigabyte_root.kind == FREE_BYTES
    assert gigabyte_root.value == 20 * 1024**3

    media_mounts = {t.mount for t in gigabyte if t.kind == PERCENT_USED}
    assert media_mounts == {
        "/media/Films",
        "/media/TechData",
        "/media/Multimedia",
        "/media/Documents",
        "/media/Comics",
        "/media/BD",
    }
    assert all(
        t.value == 90.0 for t in gigabyte if t.kind == PERCENT_USED
    )

    assert len(raspberry) == 2
    raspberry_root = next(t for t in raspberry if t.mount == "/")
    assert raspberry_root.kind == FREE_BYTES
    assert raspberry_root.value == 2 * 1024**3

    backup = next(t for t in raspberry if t.mount == "/media/BACKUP")
    assert backup.kind == PERCENT_USED
    assert backup.value == 90.0

    # Case-sensitive on purpose — `socket.gethostname()` returns
    # exactly what `hostname` printed, and a lowercase "gigabyte"
    # matching it by accident would hide a real typo the day the
    # owner's actual hostname changes case.
    assert register.for_host("gigabyte") == ()
    assert register.for_host("Raspberry") == ()


def test_invalid_yaml_syntax_is_reported_as_a_value_error(tmp_path: Path):
    """
    `yaml.safe_load` raises `yaml.YAMLError`, a type
    `aistack.cli.runtime_diagnose.storage_thresholds` is not
    documented to catch — this loader folds it into `ValueError`,
    same as a missing field, so that boundary has one exception type
    to handle rather than two.
    """

    path = write(tmp_path / "broken.yml", "hosts: [not, valid,\n")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_storage_thresholds_yaml(path)
