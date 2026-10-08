"""
`python -m aistack.cli.healthcheck` — Docker's healthcheck of the web
container (1.10, `docker-compose.yml`): asks `/healthz` on the
local-network port `instance_config.yml` declares (`web_lan`), on this
host. Exit 0 when it answers `ok`, 1 otherwise, with the reason on one
line (`docker inspect` keeps it). Light on purpose — it runs every 30 s:
it reads one declaration and opens one connection, nothing more.
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

from aistack.config import configured
from aistack.instance.yaml.store import load_instance_config_yaml

INSTANCE_CONFIG = configured(Path(__file__).resolve().parents[1] / "instance" / "definitions" / "instance_config.yml")
LAN_SERVICE = "web_lan"


def main(argv: list[str] | None = None, timeout: float = 5.0) -> int:
    try:
        port = load_instance_config_yaml(INSTANCE_CONFIG).service_ports[LAN_SERVICE]
    except (OSError, ValueError, KeyError) as error:
        print(f"no LAN port declared: {error}")
        return 1
    url = f"http://127.0.0.1:{port}/healthz"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as answer:  # noqa: S310 - fixed local URL
            body = answer.read(64).decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as error:
        print(f"{url}: HTTP {error.code}")
        return 1
    except OSError as error:
        print(f"{url}: {error}")
        return 1
    print(body)
    return 0 if body == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
