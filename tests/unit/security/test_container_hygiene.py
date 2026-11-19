"""What the containers may do to the host, read from docker inspect and judged (ADR-0028 T2a)."""

from __future__ import annotations

import json
import subprocess

from aistack.security.definition import SecurityDefinition
from aistack.security.findings import INFORMATION, WATCH
from aistack.security.hygiene import (
    CAPABILITIES,
    DOCKER_SOCKET,
    HOST_MOUNTS,
    HOST_NAMESPACES,
    PRIVILEGED,
    assess_hygiene,
    parse_inspect,
    propose_accepted,
    read_containers,
)


def _entry(name: str, image: str = "img", host: dict | None = None, mounts: list | None = None) -> dict:
    return {"Name": f"/{name}", "Config": {"Image": image, "Env": ["SECRET=never-shown"]}, "HostConfig": host or {}, "Mounts": mounts or []}


def _inspect(*entries: dict) -> str:
    return json.dumps(list(entries))


def test_each_kind_of_risk_is_read() -> None:
    containers = parse_inspect(
        _inspect(
            _entry("a", host={"Privileged": True}),
            _entry("b", mounts=[{"Type": "bind", "Source": "/var/run/docker.sock", "Destination": "/var/run/docker.sock"}]),
            _entry("c", host={"PidMode": "host"}),
            _entry("d", host={"CapAdd": ["SYS_ADMIN"]}),
            _entry("e", host={"CapAdd": ["NET_ADMIN"]}),
            _entry("f", mounts=[{"Type": "bind", "Source": "/etc/ssl", "Destination": "/x"}]),
            _entry("g", mounts=[{"Type": "bind", "Source": "/srv/media", "Destination": "/m"}]),
            _entry("h", host={"NetworkMode": "host"}),
        )
    )

    assert containers is not None
    risks = {item.name: item.risks for item in containers}
    assert risks["a"] == {PRIVILEGED} and risks["b"] == {DOCKER_SOCKET} and risks["c"] == {HOST_NAMESPACES}
    assert risks["d"] == {CAPABILITIES} and risks["f"] == {HOST_MOUNTS}
    # NET_ADMIN, an ordinary media folder and the host network are not risks of these kinds.
    assert risks["e"] == frozenset() and risks["g"] == frozenset() and risks["h"] == frozenset()
    assert next(item for item in containers if item.name == "h").host_network


def test_the_root_of_the_host_is_sensitive_but_a_path_that_only_starts_alike_is_not() -> None:
    containers = parse_inspect(
        _inspect(
            _entry("root", mounts=[{"Type": "bind", "Source": "/", "Destination": "/host"}]),
            _entry("alike", mounts=[{"Type": "bind", "Source": "/etcetera", "Destination": "/x"}]),
        )
    )

    assert containers is not None
    assert [item.name for item in containers if HOST_MOUNTS in item.risks] == ["root"]


def test_a_finding_names_containers_and_images_never_the_environment() -> None:
    containers = parse_inspect(_inspect(_entry("portainer", "portainer/ce", mounts=[{"Type": "bind", "Source": "/var/run/docker.sock"}])))
    assert containers is not None

    findings = assess_hygiene(containers, SecurityDefinition())

    assert [finding.key for finding in findings] == ["hygiene.docker_socket"]
    assert findings[0].severity == WATCH and findings[0].evidence == ("portainer (portainer/ce)",)
    assert "never-shown" not in json.dumps([finding.as_dict() for finding in findings])


def test_an_accepted_risk_is_counted_not_reported() -> None:
    containers = parse_inspect(
        _inspect(
            _entry("portainer", mounts=[{"Type": "bind", "Source": "/var/run/docker.sock"}]),
            _entry("other", mounts=[{"Type": "bind", "Source": "/var/run/docker.sock"}]),
        )
    )
    assert containers is not None
    definition = SecurityDefinition(accepted={DOCKER_SOCKET: ("portainer",)})

    findings = {finding.key: finding for finding in assess_hygiene(containers, definition)}

    assert findings["hygiene.docker_socket"].evidence == ("other (img)",)
    assert findings["hygiene.accepted"].severity == INFORMATION
    assert findings["hygiene.accepted"].evidence == ("docker_socket: portainer",)


def test_host_network_containers_are_information() -> None:
    containers = parse_inspect(_inspect(_entry("ha", host={"NetworkMode": "host"})))
    assert containers is not None

    findings = assess_hygiene(containers, SecurityDefinition())

    assert [(finding.key, finding.severity) for finding in findings] == [("hygiene.host_network", INFORMATION)]


def test_containers_that_could_not_be_read_are_a_finding_never_an_absence() -> None:
    findings = assess_hygiene(None, SecurityDefinition())

    assert [(finding.key, finding.severity) for finding in findings] == [("hygiene.unreadable", WATCH)]
    assert assess_hygiene([], SecurityDefinition()) == []


def test_the_proposal_lists_what_is_not_accepted_yet() -> None:
    containers = parse_inspect(
        _inspect(
            _entry("portainer", mounts=[{"Type": "bind", "Source": "/var/run/docker.sock"}]),
            _entry("vpn", host={"Privileged": True}),
        )
    )
    assert containers is not None

    text = propose_accepted(containers, SecurityDefinition())

    assert text == "accepted:\n  privileged:\n    - vpn\n  docker_socket:\n    - portainer\n"
    assert propose_accepted([], SecurityDefinition()) == "accepted: {}\n"


def test_docker_is_asked_with_read_only_commands_and_failure_is_none() -> None:
    asked: list[list[str]] = []

    def run(command, **_):
        asked.append(command)
        if command[1] == "ps":
            return subprocess.CompletedProcess(command, 0, stdout="abc\ndef\n")
        return subprocess.CompletedProcess(command, 0, stdout=_inspect(_entry("a")))

    assert [item.name for item in read_containers(run) or []] == ["a"]
    assert asked == [["docker", "ps", "-q", "--no-trunc"], ["docker", "inspect", "abc", "def"]]

    assert read_containers(lambda command, **_: subprocess.CompletedProcess(command, 1, stdout="")) is None
    assert read_containers(lambda command, **_: (_ for _ in ()).throw(OSError())) is None
    assert parse_inspect("not json") is None
