"""Where AIStack's data is to live (1.8): one choice, recorded, never moved by AIStack."""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.instance import data_location as dl


def test_a_choice_is_recorded_and_read_back(tmp_path: Path):
    path = tmp_path / dl.FILE_NAME
    dl.save(path, dl.DataLocation("/media/BD/aistack", "Fabrice", "2026-10-04T14:00:00+02:00"))

    assert dl.load(path) == dl.DataLocation("/media/BD/aistack", "Fabrice", "2026-10-04T14:00:00+02:00")
    assert path.read_text(encoding="utf-8").startswith("# AIStack")
    dl.clear(path)
    assert dl.load(path) is None


def test_the_file_lives_in_the_configuration_directory_when_there_is_one(tmp_path: Path):
    assert dl.location_file(tmp_path / "config", tmp_path) == tmp_path / "config" / dl.FILE_NAME
    assert dl.location_file(None, tmp_path) == tmp_path / dl.FILE_NAME


@pytest.mark.parametrize(
    ("target", "reason"),
    [
        ("relative/dir", "relative"),
        ("/does/not/exist", "missing"),
    ],
)
def test_a_choice_that_cannot_be_is_refused(tmp_path: Path, target: str, reason: str):
    with pytest.raises(dl.LocationRefused) as refused:
        dl.checked(target, tmp_path / "generated", size=None, free_space=None)
    assert refused.value.reason.endswith(reason)


def test_neither_the_same_directory_nor_one_inside_it(tmp_path: Path):
    current = tmp_path / "generated"
    (current / "inner").mkdir(parents=True)

    for target, reason in ((str(current), "same"), (str(current / "inner"), "inside")):
        with pytest.raises(dl.LocationRefused) as refused:
            dl.checked(target, current, size=None, free_space=None)
        assert refused.value.reason.endswith(reason)


def test_a_disk_without_room_for_the_data_is_refused(tmp_path: Path):
    (tmp_path / "target").mkdir()
    with pytest.raises(dl.LocationRefused):
        dl.checked(str(tmp_path / "target"), tmp_path / "generated", size=1000, free_space=1050)

    assert dl.checked(str(tmp_path / "target") + "/", tmp_path / "generated", size=1000, free_space=2000) == str(
        tmp_path / "target"
    )


def test_the_size_walk_gives_up_past_its_budget(tmp_path: Path):
    (tmp_path / "a").write_bytes(b"x" * 10)
    assert dl.measured_size(tmp_path) == 10
    assert dl.measured_size(tmp_path, budget=-1) is None


def test_a_git_installation_s_move_is_done_once_its_directory_is_a_link_there(tmp_path: Path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    generated = tmp_path / "reports" / "generated"
    generated.mkdir(parents=True)
    location = dl.DataLocation(str(target))

    assert dl.state(None, generated, False, {}) == dl.NONE
    assert dl.state(location, generated, False, {}) == dl.PLANNED
    generated.rmdir()
    generated.symlink_to(target)
    assert dl.state(location, generated, False, {}) == dl.DONE


def test_a_container_s_move_is_done_once_compose_mounts_the_chosen_directory():
    location = dl.DataLocation("/media/BD/aistack")
    generated = Path("/app/reports/generated")

    assert dl.state(location, generated, True, {dl.DATA_DIR_ENV: "./data"}) == dl.PLANNED
    assert dl.state(location, generated, True, {dl.DATA_DIR_ENV: "/media/BD/aistack"}) == dl.DONE


def test_the_commands_stop_copy_link_and_start_on_a_git_installation():
    lines = dl.commands(
        dl.DataLocation("/media/BD/aistack"),
        Path("/srv/aistack/AIStack/reports/generated"),
        in_container=False,
        environment={},
        owner="1000:1000",
    )

    assert lines[0].startswith("sudo systemctl stop aistack-web")
    assert "rsync -aH --info=progress2 /srv/aistack/AIStack/reports/generated/ /media/BD/aistack/" in lines[2]
    assert "mv /srv/aistack/AIStack/reports/generated /srv/aistack/AIStack/reports/generated.avant-deplacement" in lines
    assert "ln -s /media/BD/aistack /srv/aistack/AIStack/reports/generated" in lines
    assert lines[-1].startswith("sudo systemctl start aistack-web")
    assert not any(line.startswith("rm ") for line in lines)


def test_the_commands_copy_and_declare_the_directory_in_a_container():
    lines = dl.commands(
        dl.DataLocation("/media/BD/aistack"),
        Path("/app/reports/generated"),
        in_container=True,
        environment={dl.DATA_DIR_ENV: "./data"},
        owner="1000:1000",
    )

    assert lines[0] == "docker compose down"
    assert "rsync -aH --info=progress2 ./data/ /media/BD/aistack/" in lines[1]
    assert "AISTACK_DATA_DIR=/media/BD/aistack" in lines[3]
    assert lines[-1] == "docker compose up -d"
