from pathlib import Path

import pytest

from aistack.generators.filesystem.hardlink import MaterialisationReport
from aistack.generators.filesystem.yaml import (
    load_last_generation_yaml,
    save_last_generation_yaml,
)


def test_nothing_saved_yet_loads_as_none(tmp_path: Path):
    """
    The screen must be able to say plainly that nothing has
    generated yet, not paper over it with a report full of zeros
    that would read as a generation that ran and changed nothing.
    """

    assert load_last_generation_yaml(tmp_path / "absent.yml") is None


def test_a_saved_report_round_trips(tmp_path: Path):
    report = MaterialisationReport(
        linked=("AC  DC/loose.mp3",),
        relinked=("Classique/Bach/01.mp3",),
        removed=("Old/gone.mp3",),
        pruned=("Old",),
        unchanged=41,
        failed=(("Broken/x.mp3", "Permission denied"),),
        refused="",
        dry_run=False,
    )

    path = tmp_path / "last-generation.yml"

    save_last_generation_yaml(report, path)

    loaded = load_last_generation_yaml(path)

    assert loaded is not None
    assert loaded.report == report
    assert loaded.generated_at != ""


def test_the_generation_timestamp_is_recorded(tmp_path: Path):
    """
    `materialise_by_hardlink` is pure with respect to time; the
    screen needs to say *when* the last generation ran, which is
    the one fact the report itself cannot carry.
    """

    path = tmp_path / "last-generation.yml"

    save_last_generation_yaml(MaterialisationReport(), path)

    loaded = load_last_generation_yaml(path)

    assert loaded.generated_at.startswith("20")


def test_a_refusal_round_trips_too(tmp_path: Path):
    """
    The most important report to persist is the one where nothing
    was written — the owner should still see, on the next load,
    why the last click did nothing.
    """

    report = MaterialisationReport(
        refused="the selection is larger than the declared capacity",
    )

    path = tmp_path / "last-generation.yml"

    save_last_generation_yaml(report, path)

    assert load_last_generation_yaml(path).report.refused == (
        "the selection is larger than the declared capacity"
    )


def test_a_generation_file_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = tmp_path / "broken.yml"
    path.write_text("- one\n- two\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mapping"):
        load_last_generation_yaml(path)
