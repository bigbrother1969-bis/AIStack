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


def rows():
    from aistack.host.mounts import Mount, MountRow, Usage

    return [
        MountRow(Mount("/dev/sdc1", "/", "ext4", False), Usage(200, 50), ("code", "generated")),
        MountRow(Mount("nas:/backup", "/media/BACKUP", "nfs", False), Usage(9000, 4000), ()),
        MountRow(Mount("/dev/sda1", "/media/BD", "ext4", False), Usage(1800, 680), ()),
        MountRow(Mount("/dev/sdg1", "/media/ro", "ext4", True), Usage(100, 90), ()),
        MountRow(Mount("/dev/sdh1", "/config", "ext4", False), Usage(100, 90), ()),
    ]


def test_only_local_writable_disks_other_than_the_data_s_own_are_offered(tmp_path: Path):
    generated = Path("/srv/aistack/AIStack/reports/generated")

    offered = [row.mount.point for row in dl.candidates(rows(), generated, in_container=False)]

    assert offered == ["/media/BD"]


def test_in_a_container_the_read_only_host_mounts_are_offered_but_not_its_own():
    offered = [row.mount.point for row in dl.candidates(rows(), Path("/app/reports/generated"), in_container=True)]

    assert offered == ["/", "/media/BD", "/media/ro"]


def test_the_data_goes_to_one_folder_at_the_root_of_the_disk_chosen():
    offered = dl.candidates(rows(), Path("/srv/x/reports/generated"), in_container=False)

    assert dl.checked("/media/BD", offered, size=100) == "/media/BD/aistack-data"
    assert dl.target_on("/") == "/aistack-data"


def test_a_disk_not_offered_or_without_room_is_refused():
    offered = dl.candidates(rows(), Path("/srv/x/reports/generated"), in_container=False)

    for mount, size, reason in (("/media/BACKUP", 1, "unknown"), ("/elsewhere", 1, "unknown"), ("/media/BD", 650, "space")):
        with pytest.raises(dl.LocationRefused) as refused:
            dl.checked(mount, offered, size=size)
        assert refused.value.reason.endswith(reason)


def test_the_mount_of_a_path_is_the_longest_containing_it():
    assert dl.mount_of(Path("/media/BD/x"), ["/", "/media", "/media/BD"]) == "/media/BD"
    assert dl.mount_of(Path("/media/BDX"), ["/", "/media/BD"]) == "/"


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
    assert "sudo mkdir -p /media/BD/aistack" in lines
    assert "rsync -aH --info=progress2 /srv/aistack/AIStack/reports/generated/ /media/BD/aistack/" in lines[3]
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
    assert lines[1] == "sudo mkdir -p /media/BD/aistack"
    assert "rsync -aH --info=progress2 ./data/ /media/BD/aistack/" in lines[2]
    assert "AISTACK_DATA_DIR=/media/BD/aistack" in lines[4]
    assert lines[-1] == "docker compose up -d"
