from aistack.contracts.readme_exporter import (
    ReadmeExporter,
)


class DummyReadmeExporter(ReadmeExporter):

    def export(self) -> str:
        return "AIStack"


def test_readme_exporter_contract():

    exporter = DummyReadmeExporter()

    assert exporter.export() == "AIStack"
