from pathlib import Path

from aistack.context_bundle.service import (
    DefaultContextBundleService,
)


class FakeTransfer:

    def __init__(self):
        self.transferred = None


    def transfer(
        self,
        source: Path,
    ) -> bool:

        self.transferred = source

        return True



def test_context_bundle_service_transfers_generated_bundle(
    tmp_path,
):

    source = tmp_path / "knowledge"

    source.mkdir()

    (source / "principle.md").write_text(
        "# Principle\n",
        encoding="utf-8",
    )


    output = tmp_path / "bundle.zip"


    transfer = FakeTransfer()


    service = DefaultContextBundleService(
        transfer_service=transfer,
    )


    service.generate(
        source,
        output,
        "commit123",
    )


    assert output.exists()

    assert transfer.transferred == output
