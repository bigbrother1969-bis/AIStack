"""
`aistack.web.server` — one process, two sockets (`ADR-0012` § 3).

The exposure guards decide on the local port uvicorn reports for each
connection. The test client only imitates that; the last test here
binds two real sockets and serves them from one uvicorn server, so the
decision is proven on the address a real connection arrives at.
"""

from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import uvicorn
from fastapi import APIRouter

from aistack.web.app import create_app
from aistack.web.exposure import LAN_ONLY, Listeners, include
from aistack.i18n import Language, Languages
from aistack.web.server import INSTANCE_CONFIG, bind, listeners_from

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)



def test_the_listeners_are_the_instance_s_declared_ports():
    listeners = listeners_from(INSTANCE_CONFIG)

    assert listeners.public_port == 8183
    assert listeners.lan_port == 8186


def test_an_instance_without_a_lan_port_is_refused(tmp_path: Path):
    config = tmp_path / "instance_config.yml"
    config.write_text("lan_hostname: GIGABYTE\nservice_ports:\n  console: 8183\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no port for web_lan"):
        listeners_from(config)


def fetch(port: int, path: str) -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as reply:
            return reply.status
    except urllib.error.HTTPError as refused:
        return refused.code


def test_two_real_sockets_one_server(generated: Path):
    public = bind("127.0.0.1", 0)
    lan = bind("127.0.0.1", 0)
    listeners = Listeners(public_port=public.getsockname()[1], lan_port=lan.getsockname()[1])

    app = create_app(generated, listeners, LANGUAGES)
    router = APIRouter(dependencies=[LAN_ONLY])

    @router.get("/lan-screen")
    def lan_screen() -> dict[str, str]:
        return {"history": "shown"}

    include(app, router)

    server = uvicorn.Server(uvicorn.Config(app, proxy_headers=False, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [public, lan]}, daemon=True)
    thread.start()

    try:
        deadline = time.monotonic() + 10

        while not server.started:
            assert time.monotonic() < deadline, "uvicorn did not start"
            time.sleep(0.05)

        assert fetch(listeners.public_port, "/console.html") == 200
        assert fetch(listeners.lan_port, "/console.html") == 200
        assert fetch(listeners.lan_port, "/lan-screen") == 200
        assert fetch(listeners.public_port, "/lan-screen") == 404
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        public.close()
        lan.close()
