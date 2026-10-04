"""
The image runs AIStack (ADR-0017 § 2, § 3): the compose file's six
services, each a command the entrypoint knows, on the host network with
the socket, the configuration and the data mounted.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SERVICES = {"web", "events", "diff", "digest", "packages", "priority"}


def compose() -> dict:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def entrypoint_commands() -> dict[str, str]:
    text = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
    return dict(re.findall(r"^\s*(\w+)\)\s*exec python -m ([\w.]+)", text, re.M))


def test_the_six_processes_are_six_services_of_one_image():
    services = compose()["services"]

    assert SERVICES <= set(services)
    images = {services[name]["image"] for name in SERVICES}
    assert images == {"bigbrother1969/aistack-core:${AISTACK_VERSION:?set AISTACK_VERSION in .env}"}
    for name in SERVICES:
        assert services[name]["command"] == [name]
        assert services[name]["network_mode"] == "host"
        assert services[name]["restart"] == "unless-stopped"
    assert services["validate"]["profiles"] == ["tools"]


def test_every_service_sees_the_socket_its_configuration_and_its_data():
    volumes = compose()["x-aistack"]["volumes"]

    assert "/var/run/docker.sock:/var/run/docker.sock" in volumes
    assert "./config:/config" in volumes
    assert "${AISTACK_DATA_DIR:-./data}:/app/reports/generated" in volumes
    host_paths = [volume for volume in volumes if volume.startswith("/") and "docker.sock" not in volume]
    assert host_paths and all(volume.endswith(":ro") for volume in host_paths)
    for host_path in host_paths:
        source, target, _ = host_path.split(":")
        assert source == target  # the same path, as declarations name it


def test_every_entrypoint_command_names_a_real_module():
    commands = entrypoint_commands()

    assert SERVICES - {"web"} <= set(commands)
    for module in commands.values():
        assert importlib.util.find_spec(module) is not None, module
    assert "aistack.web.server" in (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")


def test_the_image_starts_the_application_with_its_configuration_directory():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert 'ENTRYPOINT ["aistack-entrypoint"]' in dockerfile
    assert 'CMD ["web"]' in dockerfile
    assert "ENV AISTACK_CONFIG_DIR=/config" in dockerfile
    assert "/usr/local/bin/docker" in dockerfile


def test_secrets_never_enter_the_build_context():
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert ".env.*" in ignored and "config" in ignored and "data" in ignored
