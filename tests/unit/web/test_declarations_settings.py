"""Settings: a shipped declaration that changed since the owner's copy (1.9)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.config import shipped_definitions
from aistack.instance.declarations import follow
from tests.unit.web.test_rights import build, client
from tests.unit.web_signed_in import signed_in


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "config"
    directory.mkdir()
    monkeypatch.setenv("AISTACK_CONFIG_DIR", str(directory))
    monkeypatch.setenv("AISTACK_CONFIG_HOST_DIR", "./config")
    return directory


def _changed(config: Path) -> str:
    """The owner's own file, then a seen version that is not today's shipped one."""

    source = next(path for path in shipped_definitions() if path.name == "pra_tests.yml")
    (config / "pra_tests.yml").write_text("max_age_days: 30\nservices: []\n", encoding="utf-8")
    follow(config, [source])
    (config / ".shipped-seen.json").write_text('{"pra_tests.yml": "older"}\n', encoding="utf-8")
    return source.name


def test_nothing_changed_says_so(tmp_path: Path, config: Path):
    page = signed_in(client(build(tmp_path))).get("/settings?lang=en").text

    assert "Shipped declarations" in page
    assert "No shipped declaration changed since you last saw it." in page


def test_a_changed_declaration_is_shown_with_its_difference_and_can_be_marked_seen(tmp_path: Path, config: Path):
    name = _changed(config)
    web = signed_in(client(build(tmp_path)))

    page = web.get("/settings?lang=en").text
    assert f"The shipped version of {name} changed since your copy." in page
    assert "-max_age_days: 30" in page
    assert f"docker compose cp web:/app/src/aistack/pra/definitions/{name} ./config/{name}" in page

    answer = web.post("/settings/declarations/seen", data={"name": name})
    assert answer.status_code == 303
    assert answer.headers["location"] == f"/settings?declaration={name}#declarations"
    assert "No shipped declaration changed" in web.get("/settings?lang=en").text
    assert (config / "pra_tests.yml").read_text(encoding="utf-8") == "max_age_days: 30\nservices: []\n"


def test_without_a_configuration_directory_there_is_no_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AISTACK_CONFIG_DIR", raising=False)

    assert "Shipped declarations" not in signed_in(client(build(tmp_path))).get("/settings?lang=en").text
