from pathlib import Path

from aistack.contracts.readme_exporter import ReadmeExporter


ROOT = Path(__file__).resolve().parents[4]

README_SOURCE = ROOT / "README.md"


class ReadmeBundleExporter(ReadmeExporter):
    """
    Export the governed AIStack project README.
    """

    def export(self) -> str:
        if not README_SOURCE.is_file():
            raise FileNotFoundError(
                f"Project README not found: {README_SOURCE}"
            )

        return README_SOURCE.read_text(
            encoding="utf-8",
        )
