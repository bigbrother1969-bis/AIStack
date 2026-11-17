"""Settings: the declarations edited by hand, and those their loader does not read (lot 7.4, ADR-0027 § 12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.config import shipped_definitions
from aistack.declaration import observe
from aistack.kernel.bootstrap.default import create_kernel
from tests.unit.web.test_rights import build, client
from tests.unit.web_signed_in import signed_in

NAME = "pra_tests.yml"


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "config"
    directory.mkdir()
    monkeypatch.setenv("AISTACK_CONFIG_DIR", str(directory))
    monkeypatch.setenv("AISTACK_CONFIG_HOST_DIR", "./config")
    return directory


def _pass(config: Path, generated: Path) -> None:
    shipped = shipped_definitions()
    changes = observe.observe(config, generated, shipped)
    observe.apply(create_kernel().services.transactions, config, generated, changes)


def _shipped_text() -> str:
    return next(path for path in shipped_definitions() if path.name == NAME).read_text(encoding="utf-8")


def test_nothing_recorded_says_so(tmp_path: Path, config: Path) -> None:
    page = signed_in(client(build(tmp_path))).get("/settings?lang=en").text

    assert "Declarations edited by hand" in page
    assert "No edit by hand recorded." in page
    assert "Not read now" not in page


def test_an_edit_by_hand_is_shown_with_its_difference(tmp_path: Path, config: Path) -> None:
    text = _shipped_text()
    (config / NAME).write_text(text, encoding="utf-8")
    _pass(config, tmp_path)
    (config / NAME).write_text(text + "# my own line\n", encoding="utf-8")
    _pass(config, tmp_path)

    page = signed_in(client(build(tmp_path))).get("/settings?lang=en").text

    assert f"<code>{NAME}</code>" in page
    assert "+# my own line" in page
    assert "Read by its loader." in page
    assert "Not read now" not in page


def test_a_file_the_loader_does_not_read_is_shown_first_with_the_last_valid_copy(tmp_path: Path, config: Path) -> None:
    text = _shipped_text()
    (config / NAME).write_text(text, encoding="utf-8")
    _pass(config, tmp_path)
    (config / NAME).write_text("a: [unclosed\n", encoding="utf-8")
    _pass(config, tmp_path)

    page = signed_in(client(build(tmp_path))).get("/settings?lang=fr").text

    assert "Non lues en ce moment" in page
    assert f"{NAME}.avant-observe-" in page
    assert "Non lue par son chargeur" in page
    assert "unclosed" in page  # the difference shows the owner his own edit; the record never held it


def test_without_a_configuration_directory_there_is_no_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AISTACK_CONFIG_DIR", raising=False)

    assert "Declarations edited by hand" not in signed_in(client(build(tmp_path))).get("/settings?lang=en").text
