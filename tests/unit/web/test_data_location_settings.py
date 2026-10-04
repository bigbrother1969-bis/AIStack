"""Settings: choosing where AIStack's data lives (1.8)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from aistack.instance import data_location as dl
from tests.unit.web.test_rights import build, client
from tests.unit.web_signed_in import as_user, signed_in


def app_with(tmp_path: Path):
    app = build(tmp_path)
    app.state.storage = lambda generated_dir: []
    app.state.paths = dataclasses.replace(app.state.paths, data_location=tmp_path / dl.FILE_NAME)
    return app


def test_an_administrator_records_a_location_and_sees_the_commands(tmp_path: Path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    (tmp_path / "data").mkdir()
    app = app_with(tmp_path / "data")
    web = signed_in(client(app), name="Admin")

    answer = web.post("/settings/storage/location", data={"target": str(target), "action": "save"})
    assert answer.status_code == 303
    assert answer.headers["location"] == "/settings?storage=saved#data-location"

    recorded = dl.load(tmp_path / "data" / dl.FILE_NAME)
    assert recorded is not None and recorded.target == str(target) and recorded.chosen_by == "Admin"

    page = web.get("/settings?lang=en&storage=saved").text
    assert "Location saved." in page
    assert "move planned, not done yet" in page
    assert f"ln -s {target}" in page and "rsync -aH" in page


def test_a_refused_location_says_why_and_records_nothing(tmp_path: Path):
    app = app_with(tmp_path)
    web = signed_in(client(app))

    answer = web.post("/settings/storage/location", data={"target": "/does/not/exist", "action": "save"})

    assert answer.headers["location"] == "/settings?storage=missing#data-location"
    assert dl.load(tmp_path / dl.FILE_NAME) is None
    assert "this directory does not exist" in web.get("/settings?lang=en&storage=missing").text


def test_cancelling_forgets_the_choice(tmp_path: Path):
    app = app_with(tmp_path)
    dl.save(tmp_path / dl.FILE_NAME, dl.DataLocation("/somewhere"))
    web = signed_in(client(app))

    web.post("/settings/storage/location", data={"action": "clear"})

    assert dl.load(tmp_path / dl.FILE_NAME) is None


def test_a_user_can_neither_see_nor_choose(tmp_path: Path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    app = app_with(tmp_path)
    web = as_user(client(app))

    assert web.post("/settings/storage/location", data={"target": str(target)}).status_code == 403
    assert dl.load(tmp_path / dl.FILE_NAME) is None
    assert "Where AIStack" not in web.get("/settings?lang=en").text
