"""Settings: choosing where AIStack's data lives (1.8) — a disk, from a list."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from aistack.host.mounts import Mount, MountRow, Usage
from aistack.instance import data_location as dl
from tests.unit.web.test_rights import build, client
from tests.unit.web_signed_in import as_user, signed_in


def app_with(tmp_path: Path, free: int = 2**40):
    generated = tmp_path / "data"
    generated.mkdir(exist_ok=True)
    app = build(generated)
    rows = [
        MountRow(Mount("/dev/sdc1", "/", "ext4", False), Usage(2**41, 2**39), ("generated",)),
        MountRow(Mount("/dev/sda1", "/media/BD", "ext4", False), Usage(2**41, free), ()),
        MountRow(Mount("nas:/b", "/media/BACKUP", "nfs", False), Usage(2**41, 2**40), ()),
    ]
    app.state.storage = lambda generated_dir: rows
    app.state.paths = dataclasses.replace(app.state.paths, data_location=tmp_path / dl.FILE_NAME)
    return app


def test_the_disks_are_offered_in_a_list_with_their_free_space(tmp_path: Path):
    page = signed_in(client(app_with(tmp_path))).get("/settings?lang=en").text

    assert '<select name="mount"' in page
    assert '<option value="/media/BD">/media/BD — 1.0 Tio free</option>' in page
    assert 'value="/media/BACKUP"' not in page and '<option value="/">' not in page
    assert 'type="text" name="target"' not in page


def test_an_administrator_records_a_disk_and_sees_the_commands(tmp_path: Path):
    app = app_with(tmp_path)
    web = signed_in(client(app), name="Admin")

    answer = web.post("/settings/storage/location", data={"mount": "/media/BD", "action": "save"})
    assert answer.status_code == 303
    assert answer.headers["location"] == "/settings?storage=saved#data-location"

    recorded = dl.load(tmp_path / dl.FILE_NAME)
    assert recorded is not None and recorded.target == "/media/BD/aistack-data" and recorded.chosen_by == "Admin"

    page = web.get("/settings?lang=en&storage=saved").text
    assert "Location saved." in page
    assert "move planned, not done yet" in page
    assert '<option value="/media/BD" selected>' in page
    assert "sudo mkdir -p /media/BD/aistack-data" in page and "ln -s /media/BD/aistack-data" in page


def test_a_disk_not_offered_is_refused_and_nothing_recorded(tmp_path: Path):
    web = signed_in(client(app_with(tmp_path)))

    answer = web.post("/settings/storage/location", data={"mount": "/media/BACKUP", "action": "save"})

    assert answer.headers["location"] == "/settings?storage=unknown#data-location"
    assert dl.load(tmp_path / dl.FILE_NAME) is None
    assert "this disk is not in the list offered" in web.get("/settings?lang=en&storage=unknown").text


def test_a_disk_without_room_is_refused(tmp_path: Path):
    (tmp_path / "data" ).mkdir()
    (tmp_path / "data" / "big").write_bytes(b"x" * 1000)
    web = signed_in(client(app_with(tmp_path, free=500)))

    answer = web.post("/settings/storage/location", data={"mount": "/media/BD", "action": "save"})

    assert answer.headers["location"] == "/settings?storage=space#data-location"


def test_cancelling_forgets_the_choice(tmp_path: Path):
    app = app_with(tmp_path)
    dl.save(tmp_path / dl.FILE_NAME, dl.DataLocation("/media/BD/aistack-data"))
    web = signed_in(client(app))

    web.post("/settings/storage/location", data={"action": "clear"})

    assert dl.load(tmp_path / dl.FILE_NAME) is None


def test_a_user_can_neither_see_nor_choose(tmp_path: Path):
    app = app_with(tmp_path)
    web = as_user(client(app))

    assert web.post("/settings/storage/location", data={"mount": "/media/BD"}).status_code == 403
    assert dl.load(tmp_path / dl.FILE_NAME) is None
    assert "Where AIStack" not in web.get("/settings?lang=en").text
