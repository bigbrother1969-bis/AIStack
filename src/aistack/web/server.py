"""
`python -m aistack.web.server` — AIStack's single web process
(`ADR-0012` § 3).

One uvicorn server, two sockets bound before it starts: the public
port and the LAN port, both read from `instance_config.yml`
(`service_ports.console` and `service_ports.web_lan`), never typed
here. uvicorn reports, per connection, the local address the request
arrived on, which is what `aistack.web.exposure` decides on.

`proxy_headers` is off: nothing this process decides depends on a
header the proxy sets, and the client address it would rewrite is not
used.
"""

from __future__ import annotations

import argparse
import socket
from pathlib import Path

import uvicorn

from aistack.instance.yaml.store import load_instance_config_yaml
from aistack.web.app import create_app
from aistack.web.exposure import Listeners

INSTANCE_CONFIG = (
    Path(__file__).resolve().parents[1] / "instance" / "definitions" / "instance_config.yml"
)

PUBLIC_SERVICE = "console"
LAN_SERVICE = "web_lan"


def listeners_from(instance_config: Path) -> Listeners:
    """The two ports this process serves, as `instance_config.yml` declares them."""

    config = load_instance_config_yaml(instance_config)

    for service in (PUBLIC_SERVICE, LAN_SERVICE):
        if service not in config.service_ports:
            raise ValueError(f"{instance_config} declares no port for {service}")

    return Listeners(
        public_port=config.service_ports[PUBLIC_SERVICE],
        lan_port=config.service_ports[LAN_SERVICE],
    )


def bind(host: str, port: int) -> socket.socket:
    listening = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listening.bind((host, port))
    listening.listen(128)
    listening.set_inheritable(True)

    return listening


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m aistack.web.server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--generated-dir", type=Path, default=Path("reports/generated"))
    parser.add_argument("--instance-config", type=Path, default=INSTANCE_CONFIG)
    arguments = parser.parse_args(argv)

    listeners = listeners_from(arguments.instance_config)
    app = create_app(arguments.generated_dir.resolve(), listeners)

    sockets = [
        bind(arguments.host, listeners.public_port),
        bind(arguments.host, listeners.lan_port),
    ]

    print(
        f"AIStack web serving {arguments.generated_dir} — public port "
        f"{listeners.public_port}, LAN port {listeners.lan_port}",
        flush=True,
    )

    server = uvicorn.Server(uvicorn.Config(app, proxy_headers=False))
    server.run(sockets=sockets)


if __name__ == "__main__":
    main()
