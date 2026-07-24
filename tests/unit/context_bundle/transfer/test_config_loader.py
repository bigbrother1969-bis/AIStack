from pathlib import Path

from aistack.context_bundle.transfer.config_loader import (
    load_transfer_configuration,
)


def test_load_transfer_configuration(tmp_path):

    config = tmp_path / "transfer.yml"

    config.write_text(
        """
context_bundle:
  transfer:
    enabled: true
    strategy: ssh
    target:
      host: laptop
      user: big-brother
      path: "~/Téléchargements"
""",
        encoding="utf-8",
    )


    result = load_transfer_configuration(
        config
    )


    assert result.enabled is True

    assert result.host == "laptop"

    assert result.user == "big-brother"

    assert result.destination_path == "~/Téléchargements"
