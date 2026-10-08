from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aistack.cli import healthcheck
from aistack.i18n import Language, Languages
from aistack.web.app import create_app
from aistack.web.exposure import Listeners

LISTENERS = Listeners(public_port=8183, lan_port=8186)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"),))


def _client(generated_dir: Path, port: int = 8186) -> TestClient:
    app = create_app(generated_dir, LISTENERS, LANGUAGES, phase="development")
    return TestClient(app, base_url=f"http://testserver:{port}")


def test_healthz_says_ok_without_a_session(tmp_path: Path):
    reply = _client(tmp_path).get("/healthz")

    assert reply.status_code == 200 and reply.text == "ok\n"


def test_healthz_says_when_the_data_directory_is_gone(tmp_path: Path):
    reply = _client(tmp_path / "missing").get("/healthz")

    assert reply.status_code == 503


def test_healthz_does_not_answer_on_the_public_port(tmp_path: Path):
    assert _client(tmp_path, port=8183).get("/healthz").status_code == 404


@pytest.mark.parametrize(("status", "body", "code"), [(200, b"ok\n", 0), (503, b"no\n", 1)])
def test_the_healthcheck_command_reads_the_answer(monkeypatch, capsys, status, body, code):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - http.server's own name
            self.send_response(status)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()

    class Config:
        service_ports = {"web_lan": server.server_address[1]}

    monkeypatch.setattr(healthcheck, "load_instance_config_yaml", lambda path: Config())
    assert healthcheck.main() == code
    server.server_close()


def test_the_healthcheck_command_fails_when_nothing_answers(monkeypatch, capsys):
    class Config:
        service_ports = {"web_lan": 9}  # discard port: nothing listens

    monkeypatch.setattr(healthcheck, "load_instance_config_yaml", lambda path: Config())
    assert healthcheck.main(timeout=1) == 1
