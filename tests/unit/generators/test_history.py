from pathlib import Path

from aistack.generators.history import write_artifact_with_history


def test_the_latest_path_carries_the_content_exactly_as_before(tmp_path: Path):
    """
    Every existing reader of a generator's `output_path` — the four
    `tests/unit/cli/test_the_provider_commands_run.py` tests among
    them — must see no change: the fixed path still carries the
    newest content, written the same way it always was.
    """

    latest_path = tmp_path / "reports" / "generated" / "docker-runtime-catalog.json"

    write_artifact_with_history("first\n", latest_path)

    assert latest_path.read_text(encoding="utf-8") == "first\n"


def test_a_second_write_does_not_erase_the_first(tmp_path: Path):
    """
    The defect this closes: all four provider-CLI generators used
    to overwrite their one output file on every run, destroying the
    previous observation. This is the one behaviour the fix exists
    for.
    """

    latest_path = tmp_path / "reports" / "generated" / "docker-runtime-catalog.json"

    write_artifact_with_history("first\n", latest_path)
    _, second_history_path = write_artifact_with_history("second\n", latest_path)

    history_dir = latest_path.parent / "history" / "docker-runtime-catalog"
    history_files = sorted(history_dir.glob("*.json"))

    assert latest_path.read_text(encoding="utf-8") == "second\n"
    assert len(history_files) == 2
    assert {f.read_text(encoding="utf-8") for f in history_files} == {
        "first\n",
        "second\n",
    }
    assert second_history_path in history_files


def test_history_files_live_in_a_subdirectory_named_after_the_artifact(
    tmp_path: Path,
):
    """
    `reports/generated/` must not fill with hundreds of same-stem
    files as a command is run over time — history for
    `docker-runtime-catalog.json` lives in its own
    `history/docker-runtime-catalog/` subdirectory, one per artifact
    kind, so two providers' histories never mix.
    """

    catalog_path = tmp_path / "reports" / "generated" / "docker-runtime-catalog.json"
    observation_path = (
        tmp_path / "reports" / "generated" / "docker-provider-observation.json"
    )

    write_artifact_with_history("catalog\n", catalog_path)
    write_artifact_with_history("observation\n", observation_path)

    generated = catalog_path.parent

    assert (generated / "history" / "docker-runtime-catalog").is_dir()
    assert (generated / "history" / "docker-provider-observation").is_dir()

    catalog_history = list((generated / "history" / "docker-runtime-catalog").glob("*"))
    assert len(catalog_history) == 1
    assert catalog_history[0].read_text(encoding="utf-8") == "catalog\n"


def test_the_history_filename_is_a_filesystem_safe_timestamp(tmp_path: Path):
    """
    An ISO 8601 timestamp carries `:`, which a path cannot. The
    history filename must still be parseable back as a timestamp —
    only the separator changes.
    """

    latest_path = tmp_path / "reports" / "generated" / "docker-runtime-catalog.json"

    _, history_path = write_artifact_with_history("content\n", latest_path)

    assert ":" not in history_path.name
    assert history_path.name.endswith("Z.json")
    # YYYY-MM-DDTHH-MM-SSZ.json
    assert len(history_path.stem) == len("2026-09-03T18-05-00Z")


def test_two_writes_in_the_same_second_both_survive(tmp_path: Path, monkeypatch):
    """
    Found by this test itself: the first version of this function
    used a second-resolution timestamp with no collision handling,
    and two calls landing in the same second produced the same
    filename — the second silently overwrote the first. That is
    exactly the loss "keep everything, indefinitely" was decided
    against, so it is asserted directly rather than left to luck.
    """

    import aistack.generators.history as history_module

    class FrozenDatetime(history_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 3, 18, 5, 0, tzinfo=tz)

    monkeypatch.setattr(history_module, "datetime", FrozenDatetime)

    latest_path = tmp_path / "reports" / "generated" / "docker-runtime-catalog.json"

    write_artifact_with_history("first\n", latest_path)
    write_artifact_with_history("second\n", latest_path)
    write_artifact_with_history("third\n", latest_path)

    history_dir = latest_path.parent / "history" / "docker-runtime-catalog"
    history_files = sorted(history_dir.glob("*.json"))

    assert len(history_files) == 3
    assert {f.read_text(encoding="utf-8") for f in history_files} == {
        "first\n",
        "second\n",
        "third\n",
    }


def test_returns_both_paths_it_wrote(tmp_path: Path):
    latest_path = tmp_path / "reports" / "generated" / "docker-runtime-catalog.json"

    returned_latest, returned_history = write_artifact_with_history(
        "content\n", latest_path
    )

    assert returned_latest == latest_path
    assert returned_history.exists()
    assert returned_history.parent.name == "docker-runtime-catalog"


def test_an_observation_identical_to_the_last_adds_no_copy(tmp_path: Path):
    """
    Measured on the reference host on 2026-11-07: `history/console` held
    about 916 MB of identical copies. When nothing changed between two
    runs, the second keeps no new file; the newest copy is returned and
    the fixed path still carries the content.
    """

    latest_path = tmp_path / "reports" / "generated" / "console.html"

    _, first = write_artifact_with_history("same\n", latest_path)
    _, second = write_artifact_with_history("same\n", latest_path)
    _, third = write_artifact_with_history("same\n", latest_path)

    history_dir = latest_path.parent / "history" / "console"
    assert len(list(history_dir.glob("*.html"))) == 1
    assert second == first == third
    assert latest_path.read_text(encoding="utf-8") == "same\n"


def test_a_change_after_identical_runs_is_kept_and_so_is_a_return(tmp_path: Path, monkeypatch):
    """
    Only a *difference* is a new observation: A, A, B, B, A keeps three
    copies, so going back to a past state is still recorded.
    """

    import aistack.generators.history as history_module

    ticks = iter(range(100))

    class Stepping(history_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 15, 10, 0, next(ticks), tzinfo=tz)

    monkeypatch.setattr(history_module, "datetime", Stepping)

    latest_path = tmp_path / "reports" / "generated" / "console.html"
    for content in ("A\n", "A\n", "B\n", "B\n", "A\n"):
        write_artifact_with_history(content, latest_path)

    history_dir = latest_path.parent / "history" / "console"
    kept = [f.read_text(encoding="utf-8") for f in sorted(history_dir.glob("*.html"))]
    assert kept == ["A\n", "B\n", "A\n"]


def test_identical_content_without_a_copy_still_gets_one(tmp_path: Path):
    """
    A history someone cleared (or one that never existed beside a
    `latest` file) must not stay empty just because the content did not
    change: the first write after that records the observation.
    """

    import shutil

    latest_path = tmp_path / "reports" / "generated" / "console.html"
    write_artifact_with_history("same\n", latest_path)
    shutil.rmtree(latest_path.parent / "history")

    _, again = write_artifact_with_history("same\n", latest_path)

    assert again.exists()
    assert again.read_text(encoding="utf-8") == "same\n"
