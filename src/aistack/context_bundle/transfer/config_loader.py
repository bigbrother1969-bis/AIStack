from pathlib import Path
import yaml

from aistack.context_bundle.transfer.configuration import (
    DefaultBundleTransferConfiguration,
)


def load_transfer_configuration(
    path: Path,
) -> DefaultBundleTransferConfiguration:

    data = yaml.safe_load(
        path.read_text(
            encoding="utf-8"
        )
    )

    transfer = (
        data["context_bundle"]
        ["transfer"]
    )

    target = transfer["target"]

    return DefaultBundleTransferConfiguration(
        _enabled=transfer["enabled"],
        _host=target["host"],
        _user=target["user"],
        _destination_path=target["path"],
    )
