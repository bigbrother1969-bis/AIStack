"""
*Nouveautés* inside AIStack's web application (ADR-0012, ADR-0026): what
the vigil noted is shown, a click declares or sets aside, nothing answers
on the public port, and only an administrator writes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.unit.web_signed_in import as_user, signed_in

from aistack.arrivals import state
from aistack.i18n import Language, Languages
from aistack.web.app import WebPaths, create_app
from aistack.web.exposure import Listeners

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))

CATEGORIZATION = """\
categories:
  - name: IA
    services:
      - name: Ollama
        container: ollama
"""

NOTED = {
    "updated_at": "2026-11-15T12:00:00+00:00",
    "baseline": True,
    "containers": {
        "koboldcpp": {"announced": True, "host": None, "image": "koboldcpp:local", "ports": "5001/tcp", "gpu": True, "since": "2026-11-15T11:45:00+00:00"},
        "grafana": {"announced": True, "host": "192.168.1.11", "image": "grafana/grafana"},
        "job-1": {"announced": False, "host": None},
        "ollama": {"announced": True, "host": None},
    },
    "hosts": {"192.168.1.60": {"user": "pi", "containers": 3, "since": "2026-11-15T10:00:00+00:00", "announced": True}},
}


@pytest.fixture
def paths(tmp_path: Path) -> WebPaths:
    (tmp_path / "service_categorization.yml").write_text(CATEGORIZATION, encoding="utf-8")
    (tmp_path / "arrivals.yml").write_text("confirm_passes: 2\n", encoding="utf-8")

    return WebPaths(arrivals=tmp_path / "arrivals.yml", categorization=tmp_path / "service_categorization.yml")


def client(tmp_path: Path, paths: WebPaths, port: int = LAN_PORT, reader: bool = False) -> TestClient:
    generated = tmp_path / "generated"
    app = create_app(generated, LISTENERS, LANGUAGES, paths)
    web = TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False)

    return as_user(web) if reader else signed_in(web)


def noted(tmp_path: Path) -> Path:
    directory = tmp_path / "generated"
    state.write_state(directory, NOTED)

    return directory


def test_before_the_vigil_has_noted_anything_the_page_says_so(tmp_path: Path, paths: WebPaths):
    reply = client(tmp_path, paths).get("/arrivals/?lang=en")

    assert reply.status_code == 200
    assert "has noted nothing yet" in reply.text
    assert "No container waiting." in reply.text and "No machine waiting." in reply.text
    assert 'href="/console.html?lang=en"' in reply.text


def test_it_shows_the_containers_nothing_declares_and_only_those(tmp_path: Path, paths: WebPaths):
    noted(tmp_path)

    text = client(tmp_path, paths).get("/arrivals/?lang=en").text

    assert "koboldcpp" in text and "koboldcpp:local" in text and "asks for the GPU" in text
    assert "grafana" in text and "192.168.1.11" in text
    assert "job-1" not in text  # not confirmed yet
    assert 'value="ollama"' not in text  # already declared
    assert 'value="Koboldcpp"' in text  # the suggested name
    assert "<option value=\"IA\">IA</option>" in text


def test_it_shows_a_machine_with_the_lines_to_add_to_hosts_yml(tmp_path: Path, paths: WebPaths):
    noted(tmp_path)

    text = client(tmp_path, paths).get("/arrivals/?lang=en").text

    assert "192.168.1.60" in text and "directory: hosts/machine-60" in text and "address: 192.168.1.60" in text


def test_a_machine_that_hosts_yml_or_a_decision_knows_is_not_shown(tmp_path: Path, paths: WebPaths):
    directory = noted(tmp_path)
    state.write_decisions(directory, {"ignored_containers": ["grafana"], "known_hosts": ["192.168.1.60"]})

    text = client(tmp_path, paths).get("/arrivals/?lang=en").text

    assert 'name="address"' not in text
    assert "grafana" in text  # in the "set aside" list, with its restore button
    assert text.count('value="grafana"') == 1 and "Restore" in text


def test_declaring_writes_the_file_and_says_so(tmp_path: Path, paths: WebPaths):
    noted(tmp_path)

    reply = client(tmp_path, paths).post(
        "/arrivals/declare?lang=en",
        data={"container": "koboldcpp", "name": "KoboldCpp", "category": "IA", "description": "Writing"},
    )

    assert reply.status_code == 303 and reply.headers["location"].startswith("/arrivals/?status=")
    text = paths.categorization.read_text(encoding="utf-8")
    assert "koboldcpp" in text and "Ollama" in text
    assert list(paths.categorization.parent.glob("service_categorization.yml.avant-arrivals-*"))
    assert 'value="koboldcpp"' not in client(tmp_path, paths).get("/arrivals/?lang=en").text


def test_declaring_records_who_declared_what(tmp_path: Path, paths: WebPaths):
    noted(tmp_path)

    client(tmp_path, paths).post(
        "/arrivals/declare",
        data={"container": "koboldcpp", "name": "KoboldCpp", "category": "IA", "description": ""},
    )

    record = json.loads((tmp_path / "generated" / "declaration-change.json").read_text(encoding="utf-8"))
    assert record["path"] == str(paths.categorization)
    assert record["author"] == "Tester"
    assert "koboldcpp" in record["reason"]


def test_declaring_in_a_new_category(tmp_path: Path, paths: WebPaths):
    noted(tmp_path)

    client(tmp_path, paths).post(
        "/arrivals/declare",
        data={"container": "koboldcpp", "name": "KoboldCpp", "category": "__new__", "new_category": "Écriture", "description": ""},
    )

    assert "Écriture" in paths.categorization.read_text(encoding="utf-8")


def test_an_unknown_category_writes_nothing_and_says_why(tmp_path: Path, paths: WebPaths):
    noted(tmp_path)
    before = paths.categorization.read_text(encoding="utf-8")

    reply = client(tmp_path, paths).post(
        "/arrivals/declare?lang=en",
        data={"container": "koboldcpp", "name": "KoboldCpp", "category": "Domotique", "description": ""},
    )

    assert paths.categorization.read_text(encoding="utf-8") == before
    assert "does%20not%20exist" in reply.headers["location"]


def test_setting_a_container_aside_and_restoring_it(tmp_path: Path, paths: WebPaths):
    directory = noted(tmp_path)
    web = client(tmp_path, paths)

    web.post("/arrivals/ignore", data={"container": "grafana"})
    assert state.read_decisions(directory)["ignored_containers"] == ["grafana"]

    web.post("/arrivals/restore", data={"name": "grafana"})
    assert state.read_decisions(directory)["ignored_containers"] == []


def test_noting_a_machine_as_known_and_restoring_it(tmp_path: Path, paths: WebPaths):
    directory = noted(tmp_path)
    web = client(tmp_path, paths)

    web.post("/arrivals/known", data={"address": "192.168.1.60"})
    assert state.read_decisions(directory)["known_hosts"] == ["192.168.1.60"]

    web.post("/arrivals/restore", data={"name": "192.168.1.60", "kind": "host"})
    assert state.read_decisions(directory)["known_hosts"] == []


def test_a_reader_may_look_but_not_write(tmp_path: Path, paths: WebPaths):
    directory = noted(tmp_path)
    web = client(tmp_path, paths, reader=True)
    before = paths.categorization.read_text(encoding="utf-8")

    assert web.get("/arrivals/").status_code == 200
    assert web.post("/arrivals/declare", data={"container": "koboldcpp", "name": "K", "category": "IA"}).status_code == 403
    assert web.post("/arrivals/ignore", data={"container": "grafana"}).status_code == 403
    assert web.post("/arrivals/known", data={"address": "192.168.1.60"}).status_code == 403
    assert web.post("/arrivals/restore", data={"name": "grafana"}).status_code == 403
    assert paths.categorization.read_text(encoding="utf-8") == before
    assert not (directory / state.DECISIONS_FILE).exists()


def test_the_page_is_in_french_too(tmp_path: Path, paths: WebPaths):
    assert "Conteneurs que rien ne déclare" in client(tmp_path, paths).get("/arrivals/?lang=fr").text


def test_nothing_answers_on_the_public_port(tmp_path: Path, paths: WebPaths):
    web = client(tmp_path, paths, PUBLIC_PORT)

    assert web.get("/arrivals/").status_code == 404

    for path in ("declare", "ignore", "known", "restore"):
        assert web.post(f"/arrivals/{path}", data={}).status_code == 404, path


def test_a_machine_is_never_added_by_a_click(tmp_path: Path, paths: WebPaths):
    """The screen holds no route that writes `hosts.yml`: a machine needs its collector first."""

    from aistack.web import arrivals

    assert {route.path for route in arrivals.router.routes} == {"", "/", "/declare", "/ignore", "/known", "/restore"}
