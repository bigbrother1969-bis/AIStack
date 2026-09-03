from pathlib import Path

import pytest

from aistack.application.yaml import load_application_definition_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "music_android.yml",
        """
        app_id: music_android
        title: Music Android Selection
        view_id: media-tree
        source_root: /media/TechData/Storage/Music
        target_root: /media/TechData/Storage/Music-Android
        selection_file: examples/selections/music-android-selection-real.yml
        capacity_declared_bytes: 64000000000
        syncthing:
          url: http://127.0.0.1:8384
          folder_id: music-android
          device_id: ABCDEF1
          api_key_env: SYNCTHING_API_KEY
          timeout_seconds: 5
        """,
    )

    definition = load_application_definition_yaml(path)

    assert definition.app_id == "music_android"
    assert definition.view_id == "media-tree"
    assert definition.source_root == "/media/TechData/Storage/Music"
    assert definition.target_root == "/media/TechData/Storage/Music-Android"
    assert definition.capacity_declared_bytes == 64000000000
    assert definition.syncthing is not None
    assert definition.syncthing.url == "http://127.0.0.1:8384"
    assert definition.syncthing.folder_id == "music-android"
    assert definition.syncthing.device_id == "ABCDEF1"
    assert definition.syncthing.api_key_env == "SYNCTHING_API_KEY"
    assert definition.syncthing.timeout_seconds == 5.0


def test_the_catalog_identity_is_derived_not_declared_twice(tmp_path: Path):
    """
    Nothing in this family varies a catalog's identifier
    independently of the app that produces it — the definition
    does not make a human write the app's name a second time
    under a different key.
    """

    path = write(
        tmp_path / "music_android.yml",
        """
        app_id: music_android
        title: Music Android Selection
        view_id: media-tree
        source_root: /library
        target_root: /target
        selection_file: examples/selections/s.yml
        """,
    )

    definition = load_application_definition_yaml(path)

    assert definition.catalog_id == "music_android-library"
    assert definition.catalog_title == "Music Android Selection — Library"


def test_syncthing_is_optional(tmp_path: Path):
    """
    A future member of the family need not sync to a phone at all.
    """

    path = write(
        tmp_path / "no_syncthing.yml",
        """
        app_id: other_app
        title: Other App
        view_id: media-tree
        source_root: /library
        target_root: /target
        selection_file: examples/selections/other.yml
        """,
    )

    definition = load_application_definition_yaml(path)

    assert definition.syncthing is None


def test_an_undeclared_capacity_is_read_as_zero(tmp_path: Path):
    """
    Mirrors `assess_capacity`'s own convention: an absent line and
    a line reading `0` are the same accident, and both mean *not
    declared* rather than a quota that refuses everything.
    """

    path = write(
        tmp_path / "undeclared.yml",
        """
        app_id: a
        title: A
        view_id: media-tree
        source_root: /library
        target_root: /target
        selection_file: examples/selections/a.yml
        """,
    )

    assert load_application_definition_yaml(path).capacity_declared_bytes == 0


def test_a_missing_required_field_is_named(tmp_path: Path):
    path = write(
        tmp_path / "incomplete.yml",
        """
        app_id: a
        title: A
        source_root: /library
        target_root: /target
        selection_file: examples/selections/a.yml
        """,
    )

    with pytest.raises(ValueError, match="view_id"):
        load_application_definition_yaml(path)


def test_a_syncthing_block_missing_its_own_required_field_is_named(
    tmp_path: Path,
):
    path = write(
        tmp_path / "bad_syncthing.yml",
        """
        app_id: a
        title: A
        view_id: media-tree
        source_root: /library
        target_root: /target
        selection_file: examples/selections/a.yml
        syncthing:
          folder_id: music-android
        """,
    )

    with pytest.raises(ValueError, match="syncthing.*url"):
        load_application_definition_yaml(path)


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_application_definition_yaml(path)


def test_the_real_music_android_definition_loads():
    """
    `selection_ui/definitions/music_android.yml` is not a fixture —
    it is the artefact `selection_ui/app.py` reads once the screen
    is rewired onto it (step 8). Loading it here means a typo in
    the real file is caught by the test suite rather than by the
    owner opening the screen.
    """

    repo_root = Path(__file__).resolve().parents[3]

    definition = load_application_definition_yaml(
        repo_root / "selection_ui" / "definitions" / "music_android.yml"
    )

    assert definition.app_id == "music_android"
    assert definition.view_id == "media-tree"
    assert definition.source_root == "/media/TechData/Storage/Music"
    assert definition.target_root == "/media/TechData/Storage/Music-Android"
    assert definition.capacity_declared_bytes == 64_000_000_000
    assert definition.syncthing is not None
    assert definition.syncthing.folder_id == "music-android"
    assert definition.syncthing.api_key_env == "SYNCTHING_API_KEY"
