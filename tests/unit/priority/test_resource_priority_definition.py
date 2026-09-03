from pathlib import Path

import pytest

from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    CpuThresholdDetectorDefinition,
    JellyfinDetectorDefinition,
    PriorityAppDefinition,
    ResourcePriorityDefinition,
)
from aistack.priority.yaml import (
    load_resource_priority_yaml,
    save_resource_priority_yaml,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "resource_priority.yml",
        """
        priority:
          - container: jellyfin
            normal_cpus: 3
            boosted_cpus: 4
            detector:
              type: jellyfin
              url: http://127.0.0.1:8096
              api_key_env: JELLYFIN_API_KEY
              timeout_seconds: 5
        unlimited_cpus: 4
        grace_seconds: 60
        background:
          default_throttled_cpus: 0.1
          containers:
            - name: radarr
            - name: komf
              normal_cpus: 0.5
        """,
    )

    definition = load_resource_priority_yaml(path)

    assert len(definition.priority) == 1
    jellyfin = definition.priority[0]

    assert jellyfin.container == "jellyfin"
    assert jellyfin.normal_cpus == 3.0
    assert jellyfin.boosted_cpus == 4.0

    detector = jellyfin.detector
    assert isinstance(detector, JellyfinDetectorDefinition)
    assert detector.url == "http://127.0.0.1:8096"
    assert detector.api_key_env == "JELLYFIN_API_KEY"
    assert detector.timeout_seconds == 5.0

    assert definition.unlimited_cpus == 4.0
    assert definition.grace_seconds == 60.0

    assert definition.background.default_throttled_cpus == 0.1
    assert len(definition.background.containers) == 2

    radarr, komf = definition.background.containers

    assert radarr.name == "radarr"
    assert radarr.normal_cpus is None

    assert komf.name == "komf"
    assert komf.normal_cpus == 0.5


def test_grace_seconds_defaults_when_absent(tmp_path: Path):
    """
    A definition predating this field (or one hand-written without
    it) still loads — 60 seconds was the owner's own decision before
    this field existed to carry it.
    """

    path = write(
        tmp_path / "no_grace.yml",
        """
        priority: []
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    assert load_resource_priority_yaml(path).grace_seconds == 60.0


def test_a_definition_with_no_priority_apps_is_valid(tmp_path: Path):
    """
    Not every host has a priority app configured yet — the list is
    allowed to be empty, the same way `background.containers` always
    was.
    """

    path = write(
        tmp_path / "no_priority.yml",
        """
        priority: []
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    assert load_resource_priority_yaml(path).priority == ()


def test_a_second_priority_app_can_use_the_cpu_threshold_detector(
    tmp_path: Path,
):
    path = write(
        tmp_path / "two_apps.yml",
        """
        priority:
          - container: jellyfin
            normal_cpus: 3
            boosted_cpus: 4
            detector:
              type: jellyfin
              url: http://127.0.0.1:8096
          - container: some-app
            normal_cpus: 1
            boosted_cpus: 2
            detector:
              type: cpu_threshold
              threshold_percent: 70
              sustained_seconds: 30
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    definition = load_resource_priority_yaml(path)

    assert len(definition.priority) == 2
    second = definition.priority[1]

    assert second.container == "some-app"
    detector = second.detector
    assert isinstance(detector, CpuThresholdDetectorDefinition)
    assert detector.threshold_percent == 70.0
    assert detector.sustained_seconds == 30.0


def test_cpu_threshold_detector_defaults_when_only_its_type_is_given(
    tmp_path: Path,
):
    path = write(
        tmp_path / "bare_cpu_threshold.yml",
        """
        priority:
          - container: some-app
            normal_cpus: 1
            boosted_cpus: 2
            detector:
              type: cpu_threshold
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    detector = load_resource_priority_yaml(path).priority[0].detector

    assert isinstance(detector, CpuThresholdDetectorDefinition)
    assert detector.threshold_percent == 50.0
    assert detector.sustained_seconds == 15.0


def test_jellyfin_detectors_api_key_env_and_timeout_default(tmp_path: Path):
    """
    Mirrors `SyncthingDefinition`: a jellyfin detector need not name
    an environment variable or a timeout to be valid.
    """

    path = write(
        tmp_path / "bare_jellyfin.yml",
        """
        priority:
          - container: jellyfin
            normal_cpus: 3
            boosted_cpus: 4
            detector:
              type: jellyfin
              url: http://127.0.0.1:8096
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    detector = load_resource_priority_yaml(path).priority[0].detector

    assert isinstance(detector, JellyfinDetectorDefinition)
    assert detector.api_key_env == ""
    assert detector.timeout_seconds == 5.0


def test_a_container_with_no_normal_cpus_reads_as_unlimited(tmp_path: Path):
    """
    Mirrors the real infrastructure: thirteen of the fourteen
    governed containers run with no CPU limit at all today, and
    restoring them "to normal" means removing the limit, not
    setting one to zero.
    """

    path = write(
        tmp_path / "background_unlimited.yml",
        """
        priority: []
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers:
            - name: sonarr
        """,
    )

    definition = load_resource_priority_yaml(path)

    assert definition.background.containers[0].normal_cpus is None


def test_a_missing_top_level_field_is_named(tmp_path: Path):
    path = write(
        tmp_path / "incomplete.yml",
        """
        priority: []
        """,
    )

    with pytest.raises(ValueError, match="background"):
        load_resource_priority_yaml(path)


def test_unlimited_cpus_missing_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_unlimited.yml",
        """
        priority: []
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    with pytest.raises(ValueError, match="unlimited_cpus"):
        load_resource_priority_yaml(path)


def test_a_priority_app_missing_its_own_required_field_is_named(
    tmp_path: Path,
):
    path = write(
        tmp_path / "bad_priority.yml",
        """
        priority:
          - container: jellyfin
            normal_cpus: 3
            detector:
              type: jellyfin
              url: http://127.0.0.1:8096
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    with pytest.raises(ValueError, match=r"priority\[0\].*boosted_cpus"):
        load_resource_priority_yaml(path)


def test_a_detector_missing_its_type_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_detector_type.yml",
        """
        priority:
          - container: jellyfin
            normal_cpus: 3
            boosted_cpus: 4
            detector:
              url: http://127.0.0.1:8096
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    with pytest.raises(ValueError, match=r"priority\[0\]\.detector.*type"):
        load_resource_priority_yaml(path)


def test_an_unknown_detector_type_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "unknown_detector.yml",
        """
        priority:
          - container: jellyfin
            normal_cpus: 3
            boosted_cpus: 4
            detector:
              type: something-else
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    with pytest.raises(ValueError, match="unknown detector type"):
        load_resource_priority_yaml(path)


def test_a_jellyfin_detector_missing_its_url_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_url.yml",
        """
        priority:
          - container: jellyfin
            normal_cpus: 3
            boosted_cpus: 4
            detector:
              type: jellyfin
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    with pytest.raises(ValueError, match=r"priority\[0\]\.detector.*url"):
        load_resource_priority_yaml(path)


def test_priority_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "not_a_list.yml",
        """
        priority: jellyfin
        unlimited_cpus: 4
        background:
          default_throttled_cpus: 0.1
          containers: []
        """,
    )

    with pytest.raises(ValueError, match="priority must be a list"):
        load_resource_priority_yaml(path)


def test_a_background_block_missing_its_own_required_field_is_named(
    tmp_path: Path,
):
    path = write(
        tmp_path / "bad_background.yml",
        """
        priority: []
        unlimited_cpus: 4
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
        priority: []
        unlimited_cpus: 4
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
        tmp_path / "not_a_list_containers.yml",
        """
        priority: []
        unlimited_cpus: 4
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
    a fixture — it is the artefact the étape 4 monitor
    (`aistack.cli.resource_priority_monitor`) reads. Loading it here
    means a typo in the real, hand-written file is caught by the
    test suite.
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

    assert len(definition.priority) == 1
    jellyfin = definition.priority[0]

    assert jellyfin.container == "jellyfin"
    assert jellyfin.normal_cpus == 3.0
    assert jellyfin.boosted_cpus == 4.0

    detector = jellyfin.detector
    assert isinstance(detector, JellyfinDetectorDefinition)
    assert detector.url == "http://127.0.0.1:8096"
    assert detector.api_key_env == "JELLYFIN_API_KEY"
    assert detector.timeout_seconds == 5.0

    assert definition.unlimited_cpus == 4.0
    assert definition.grace_seconds == 60.0

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


def test_saving_and_reloading_round_trips_a_jellyfin_priority_app(
    tmp_path: Path,
):
    """
    `priority_ui/app.py`'s own `/save` writes through
    `save_resource_priority_yaml` and the monitor reads back through
    `load_resource_priority_yaml` — the two must agree on every
    field, including the ones a human never types by hand
    (`api_key_env`'s empty default, `timeout_seconds`).
    """

    original = ResourcePriorityDefinition(
        priority=(
            PriorityAppDefinition(
                container="jellyfin",
                normal_cpus=3.0,
                boosted_cpus=4.0,
                detector=JellyfinDetectorDefinition(
                    url="http://127.0.0.1:8096",
                    api_key_env="JELLYFIN_API_KEY",
                    timeout_seconds=5.0,
                ),
            ),
        ),
        background=BackgroundPriorityDefinition(
            default_throttled_cpus=0.1,
            containers=(
                ContainerPriorityDefinition(name="radarr"),
                ContainerPriorityDefinition(name="komf", normal_cpus=0.5),
            ),
        ),
        unlimited_cpus=4.0,
        grace_seconds=60.0,
    )

    path = tmp_path / "round_trip.yml"
    save_resource_priority_yaml(original, path)

    assert load_resource_priority_yaml(path) == original


def test_saving_and_reloading_round_trips_a_cpu_threshold_priority_app(
    tmp_path: Path,
):
    original = ResourcePriorityDefinition(
        priority=(
            PriorityAppDefinition(
                container="some-app",
                normal_cpus=1.0,
                boosted_cpus=2.0,
                detector=CpuThresholdDetectorDefinition(
                    threshold_percent=70.0, sustained_seconds=30.0
                ),
            ),
        ),
        background=BackgroundPriorityDefinition(default_throttled_cpus=0.1),
        unlimited_cpus=4.0,
    )

    path = tmp_path / "round_trip_cpu.yml"
    save_resource_priority_yaml(original, path)

    assert load_resource_priority_yaml(path) == original


def test_saving_omits_normal_cpus_for_an_unlimited_background_container(
    tmp_path: Path,
):
    """
    `None` (unlimited) is never written as `normal_cpus: null` — it
    is written as the key's own absence, the one form
    `_load_container`'s `data.get("normal_cpus")` already reads back
    as unlimited.
    """

    original = ResourcePriorityDefinition(
        priority=(),
        background=BackgroundPriorityDefinition(
            default_throttled_cpus=0.1,
            containers=(ContainerPriorityDefinition(name="radarr"),),
        ),
        unlimited_cpus=4.0,
    )

    path = tmp_path / "unlimited.yml"
    save_resource_priority_yaml(original, path)

    raw = path.read_text(encoding="utf-8")

    assert "normal_cpus" not in raw.split("containers:")[1]


def test_saving_writes_the_files_own_documentation_comments(tmp_path: Path):
    """
    Found live on GIGABYTE, 2026-09-03
    (`claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md`): a first
    version of `save_resource_priority_yaml` used one combined
    `yaml.safe_dump`, which carries no notion of comments at all, so
    a `priority_ui` save silently stripped this file's entire
    documentation (88 lines to 29). This does not assert the exact
    wording — that is expected to be revised — only that a save
    keeps producing a documented file rather than a bare one, and
    that a comment sits above each of its four top-level sections,
    the same shape this file has always had.
    """

    original = ResourcePriorityDefinition(
        priority=(),
        background=BackgroundPriorityDefinition(
            default_throttled_cpus=0.1,
            containers=(ContainerPriorityDefinition(name="radarr"),),
        ),
        unlimited_cpus=4.0,
        grace_seconds=60.0,
    )

    path = tmp_path / "documented.yml"
    save_resource_priority_yaml(original, path)

    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    assert lines[0].startswith("#")

    for key in ("priority:", "unlimited_cpus:", "grace_seconds:", "background:"):
        line_index = next(
            i for i, line in enumerate(lines) if line == key or line.startswith(key)
        )
        assert lines[line_index - 1].startswith("#"), (
            f"no comment directly above {key!r}"
        )
