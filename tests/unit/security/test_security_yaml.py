"""The security declaration: every key optional, every port checked (ADR-0028)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.config import PACKAGE_ROOT
from aistack.security.yaml import load_security_yaml

SHIPPED = PACKAGE_ROOT / "security" / "definitions" / "security.yml"


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "security.yml"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_shipped_declaration_declares_nothing_and_knows_the_dangerous_ports() -> None:
    definition = load_security_yaml(SHIPPED)

    assert definition.declared_ports == {}
    assert 2375 in definition.critical_ports and 5432 in definition.sensitive_ports


def test_an_empty_file_declares_nothing(tmp_path: Path) -> None:
    definition = load_security_yaml(_write(tmp_path, ""))

    assert definition.declared_ports == {} and definition.max_listed == 20


def test_declared_ports_are_read_with_their_purpose(tmp_path: Path) -> None:
    definition = load_security_yaml(_write(tmp_path, "declared_ports:\n  22: SSH\n  8183: AIStack\n"))

    assert definition.declared_ports == {22: "SSH", 8183: "AIStack"}


@pytest.mark.parametrize(
    "text",
    [
        "- not a mapping\n",
        "declared_ports: [22]\n",
        "declared_ports:\n  ssh: SSH\n",
        "declared_ports:\n  70000: too high\n",
        "declared_ports:\n  0: zero\n",
        "sensitive_ports:\n  true: bool\n",
        "accepted: [portainer]\n",
        "accepted:\n  unknown_kind: [a]\n",
        "accepted:\n  docker_socket: portainer\n",
        "accepted:\n  docker_socket: [1]\n",
        "max_listed: 0\n",
        "max_listed: many\n",
    ],
)
def test_an_invalid_declaration_is_refused(tmp_path: Path, text: str) -> None:
    with pytest.raises(ValueError):
        load_security_yaml(_write(tmp_path, text))


def test_accepted_risks_are_read_by_kind(tmp_path: Path) -> None:
    definition = load_security_yaml(_write(tmp_path, "accepted:\n  docker_socket: [portainer, beszel]\n"))

    assert definition.accepted == {"docker_socket": ("portainer", "beszel")}
    assert load_security_yaml(SHIPPED).accepted == {}
