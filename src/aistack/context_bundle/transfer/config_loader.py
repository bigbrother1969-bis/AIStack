from pathlib import Path
import os
import yaml

from aistack.context_bundle.transfer.configuration import (
    DefaultBundleTransferConfiguration,
)


ENV_ENABLED = "AISTACK_TRANSFER_ENABLED"
ENV_HOST = "AISTACK_TRANSFER_HOST"
ENV_USER = "AISTACK_TRANSFER_USER"
ENV_PATH = "AISTACK_TRANSFER_PATH"


def _as_bool(value: str) -> bool:
    return value.strip().lower() in (
        "1",
        "true",
        "yes",
    )


def load_transfer_configuration(
    path: Path,
) -> DefaultBundleTransferConfiguration:
    """
    Load the transfer configuration.

    Environment variables take precedence over the file so
    that a deployment target never has to be committed into
    the governed heritage. The file provides defaults only.
    """

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

    enabled = transfer["enabled"]

    if ENV_ENABLED in os.environ:
        enabled = _as_bool(
            os.environ[ENV_ENABLED]
        )

    return DefaultBundleTransferConfiguration(
        _enabled=enabled,
        _host=os.environ.get(
            ENV_HOST,
            target["host"],
        ),
        _user=os.environ.get(
            ENV_USER,
            target["user"],
        ),
        _destination_path=os.environ.get(
            ENV_PATH,
            target["path"],
        ),
    )
