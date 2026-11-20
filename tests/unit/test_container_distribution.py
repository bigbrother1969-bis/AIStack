"""
The image runs AIStack (ADR-0017 § 2, § 3): the compose file's six
services, each a command the entrypoint knows, on the host network with
the configuration and the data mounted, and the Docker socket for every
one but the web application, which reads Docker through a read-only
proxy (ADR-0028 § 10).
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
    return dict(re.findall(r"^\s*([\w-]+)\)\s*exec python -m ([\w.]+)", text, re.M))


def test_the_six_processes_are_six_services_of_one_image():
    services = compose()["services"]

    assert SERVICES <= set(services)
    images = {services[name]["image"] for name in SERVICES}
    assert images == {"bigbrother1969/aistack-core:${AISTACK_VERSION:?set AISTACK_VERSION in .env}"}
    for name in SERVICES:
        assert services[name]["command"] == [name]
        assert services[name]["network_mode"] == "host"
        assert services[name]["restart"] == "unless-stopped"
    # The knowledge-integrity validator was retired in 2.0.0-rc2.
    # `docker-proxy` is not AIStack's image: it is what the web reads Docker through.
    assert set(services) == SERVICES | {"vigil", "restart-watch", "docker-proxy"}


def test_every_service_sees_the_socket_its_configuration_and_its_data():
    volumes = compose()["x-aistack"]["volumes"]

    assert "/var/run/docker.sock:/var/run/docker.sock" in volumes
    assert "./config:/config" in volumes
    assert "${AISTACK_DATA_DIR:-./data}:/app/reports/generated" in volumes
    host_paths = [volume for volume in volumes if volume.startswith("/") and "docker.sock" not in volume]
    # Read-only, and following the host's later mounts (`rslave`, 1.9).
    assert host_paths and all(volume.rsplit(":", 1)[1].split(",") == ["ro", "rslave"] for volume in host_paths)
    for host_path in host_paths:
        source, target, _ = host_path.split(":")
        assert source == target  # the same path, as declarations name it


SOCKET = "/var/run/docker.sock:/var/run/docker.sock"


def test_the_public_web_application_holds_no_docker_socket():
    services = compose()["services"]
    web = services["web"]

    assert SOCKET not in web["volumes"]
    assert not any("docker.sock" in str(volume) for volume in web["volumes"])
    assert web["group_add"] == []  # not in the socket's group either
    assert web["environment"]["DOCKER_HOST"] == "tcp://127.0.0.1:${AISTACK_DOCKER_PROXY_PORT:-2376}"
    assert "docker-proxy" in web["depends_on"]
    # What it keeps is what the others have, less the socket: a key given
    # beside `<<: *aistack` replaces the merged one whole, so it could drift.
    shared = [volume for volume in compose()["x-aistack"]["volumes"] if volume != SOCKET]
    assert web["volumes"] == shared
    assert web["environment"]["AISTACK_DATA_DIR"] == compose()["x-aistack"]["environment"]["AISTACK_DATA_DIR"]
    assert web["environment"]["AISTACK_CONFIG_HOST_DIR"] == "./config"
    assert web["user"] == compose()["x-aistack"]["user"]


def test_every_other_service_keeps_the_socket_and_its_group():
    # They collect, restart and apply: the web application is the one with a public listener.
    services = compose()["services"]

    for name in SERVICES - {"web"} | {"vigil", "restart-watch"}:
        assert SOCKET in services[name]["volumes"], name
        assert services[name]["group_add"] == ["${DOCKER_GID:-999}"], name


def test_the_docker_proxy_refuses_every_write_and_listens_on_the_loopback_only():
    proxy = compose()["services"]["docker-proxy"]
    settings = proxy["environment"]

    assert settings["POST"] == 0  # the write verbs: HTTP 403
    allowed = {key for key, value in settings.items() if value == 1}
    # What the web application reads, and nothing else: no exec, no build,
    # no secrets, no swarm, no system calls.
    assert allowed == {"CONTAINERS", "IMAGES", "NETWORKS", "VOLUMES", "INFO", "VERSION"}
    assert settings["EVENTS"] == 0
    for dangerous in ("EXEC", "BUILD", "COMMIT", "SECRETS", "SERVICES", "SWARM", "SYSTEM", "CONFIGS", "PLUGINS", "AUTH"):
        assert settings.get(dangerous, 0) == 0, dangerous
    assert proxy["ports"] == ["127.0.0.1:${AISTACK_DOCKER_PROXY_PORT:-2376}:2375"]
    assert proxy["volumes"] == ["/var/run/docker.sock:/var/run/docker.sock:ro"]
    assert "network_mode" not in proxy  # on its own bridge network, not the host's
    assert proxy["container_name"] == "aistack-docker-proxy"


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


def test_the_host_s_additions_are_an_example_never_committed():
    import yaml

    root = Path(__file__).resolve().parents[2]
    example = yaml.safe_load((root / "docker-compose.override.example.yml").read_text(encoding="utf-8"))

    web = example["services"]["web"]
    # No read-write host path since 2.0: the sync executor runs on the host (ADR-0022).
    assert "volumes" not in web
    assert web["deploy"]["resources"]["reservations"]["devices"][0]["driver"] == "nvidia"
    assert "/docker-compose.override.yml" in (root / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_the_preflight_reads_and_changes_nothing():
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "compose_preflight.sh"
    text = script.read_text(encoding="utf-8")

    assert script.stat().st_mode & 0o111
    for changing in (" rm ", " mv ", " cp ", "systemctl stop", "systemctl disable", "docker compose up", "> .env", "sudo "):
        assert changing not in text
