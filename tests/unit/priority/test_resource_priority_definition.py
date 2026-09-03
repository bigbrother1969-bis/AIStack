from pathlib import Path

import pytest

from aistack.priority.yaml import load_resource_priority_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "resource_priority.yml",
        """
        jellyfin:
          container: jellyfin
          normal_cpus: 3
          boosted_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers:
            - name: radarr
            - name: komf
              normal_cpus: 0.5
        """,
    )

    definition = load_resource_priority_yaml(path)

    assert definition.jellyfin.container == "jellyfin"
    assert definition.jellyfin.normal_cpus == 3.0
    assert definition.jellyfin.boosted_cpus == 4.0

    assert definition.background.default_throttled_cpus == 0.1
    assert len(definition.background.containers) == 2

    radarr, komf = definition.background.containers

    assert radarr.name == "radarr"
    assert radarr.normal_cpus is None

    assert komf.name == "komf"
    assert komf.normal_cpus == 0.5


def test_a_container_with_no_normal_cpus_reads_as_unlimited(tmp_path: Path):
    """
    Mirrors the real infrastructure: thirteen of the fourteen
    governed containers run with no CPU limit at all today, and
    restoring them "to normal" means removing the limit, not
    setting one to zero.
    """

    path = write(
        tmp_path / "resource_priority.yml",
        """
        jellyfin:
          container: jellyfin
          normal_cpus: 3
          boosted_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers:
            - name: sonarr
        """,
    )

    definition = load_resource_priority_yaml(path)

    assert definition.background.containers[0].normal_cpus is None


def test_a_definition_with_no_containers_is_valid(tmp_path: Path):
    path = write(
        tmp_path / "empty.yml",
        """
        jellyfin:
          container: jellyfin
          normal_cpus: 3
          boosted_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    assert load_resource_priority_yaml(path).background.containers == ()


def test_a_missing_top_level_field_is_named(tmp_path: Path):
    path = write(
        tmp_path / "incomplete.yml",
        """
        jellyfin:
          container: jellyfin
          normal_cpus: 3
          boosted_cpus: 4
        """,
    )

    with pytest.raises(ValueError, match="background"):
        load_resource_priority_yaml(path)


def test_a_jellyfin_block_missing_its_own_required_field_is_named(
    tmp_path: Path,
):
    path = write(
        tmp_path / "bad_jellyfin.yml",
        """
        jellyfin:
          container: jellyfin
          normal_cpus: 3
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    with pytest.raises(ValueError, match="jellyfin.*boosted_cpus"):
        load_resource_priority_yaml(path)


def test_a_background_block_missing_its_own_required_field_is_named(
    tmp_path: Path,
):
    path = write(
        tmp_path / "bad_background.yml",
        """
        jellyfin:
          container: jellyfin
          normal_cpus: 3
          boosted_cpus: 4
        background:
          containers: []
        """,
    )

    with pytest.raises(ValueError, match="background.*default_throttled_cpus"):
        load_resource_priority_yaml(path)


def test_a_container_missing_its_name_is_named_by_position(tmp_path: Path):
    path = write(
        tmp_path / "bad_container.yml",
        """
        jellyfin:
          container: jellyfin
          normal_cpus: 3
          boosted_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers:
            - name: radarr
            - normal_cpus: 0.5
        """,
    )

    with pytest.raises(ValueError, match=r"containers\[1\].*name"):
        load_resource_priority_yaml(path)


def test_containers_that_are_not_a_list_are_refused(tmp_path: Path):
    path = write(
        tmp_path / "not_a_list.yml",
        """
        jellyfin:
          container: jellyfin
          normal_cpus: 3
          boosted_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: radarr
        """,
    )

    with pytest.raises(ValueError, match="containers must be a list"):
        load_resource_priority_yaml(path)


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_resource_priority_yaml(path)


def test_the_real_resource_priority_definition_loads():
    """
    `src/aistack/priority/definitions/resource_priority.yml` is not
    a fixture — it is the artefact the future monitor (étape 4)
    will read. Loading it here means a typo in the real, hand-
    written file is caught by the test suite.
    """

    repo_root = Path(__file__).resolve().parents[3]

    definition = load_resource_priority_yaml(
        repo_root
        / "src"
        / "aistack"
        / "priority"
        / "definitions"
        / "resource_priority.yml"
    )

    assert definition.jellyfin.container == "jellyfin"
    assert definition.jellyfin.normal_cpus == 3.0
    assert definition.jellyfin.boosted_cpus == 4.0

    assert definition.background.default_throttled_cpus == 0.1

    names = [c.name for c in definition.background.containers]

    assert names == [
        "radarr",
        "sonarr",
        "lidarr",
        "readarr",
        "mylar3",
        "bazarr",
        "prowlarr",
        "autobrr",
        "qbittorrent",
        "gluetun",
        "unpackerr",
        "seerr",
        "mularr",
        "komf",
    ]

    by_name = {c.name: c for c in definition.background.containers}

    assert by_name["radarr"].normal_cpus is None
    assert by_name["komf"].normal_cpus == 0.5
