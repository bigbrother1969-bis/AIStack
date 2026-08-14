from pathlib import Path

from aistack.context_bundle.transfer.config_loader import (
    load_transfer_configuration,
)


TEMPLATE = """
context_bundle:
  transfer:
    enabled: true
    strategy: ssh
    target:
      host: laptop
      user: big-brother
      path: "~/Téléchargements"
"""


def _config(tmp_path: Path) -> Path:

    config = tmp_path / "transfer.yml"

    config.write_text(
        TEMPLATE,
        encoding="utf-8",
    )

    return config


def test_load_transfer_configuration(tmp_path, monkeypatch):

    for name in (
        "AISTACK_TRANSFER_ENABLED",
        "AISTACK_TRANSFER_HOST",
        "AISTACK_TRANSFER_USER",
        "AISTACK_TRANSFER_PATH",
    ):
        monkeypatch.delenv(name, raising=False)

    result = load_transfer_configuration(
        _config(tmp_path)
    )

    assert result.enabled is True

    assert result.host == "laptop"

    assert result.user == "big-brother"

    assert result.destination_path == "~/Téléchargements"


def test_environment_overrides_file(tmp_path, monkeypatch):
    """
    A deployment target is environment, not governed
    knowledge: the environment must win over the file.
    """

    monkeypatch.setenv("AISTACK_TRANSFER_HOST", "ci-runner")
    monkeypatch.setenv("AISTACK_TRANSFER_USER", "aistack")
    monkeypatch.setenv("AISTACK_TRANSFER_PATH", "/srv/bundles")

    result = load_transfer_configuration(
        _config(tmp_path)
    )

    assert result.host == "ci-runner"

    assert result.user == "aistack"

    assert result.destination_path == "/srv/bundles"


def test_environment_can_disable_transfer(tmp_path, monkeypatch):

    monkeypatch.setenv("AISTACK_TRANSFER_ENABLED", "false")

    result = load_transfer_configuration(
        _config(tmp_path)
    )

    assert result.enabled is False
