from aistack.context_bundle.service import (
    DefaultContextBundleService,
)


def test_context_bundle_service_generates_bundle(
    tmp_path,
):

    source = tmp_path / "knowledge"

    source.mkdir()

    # Eligibility is an allow list: the governed heritage
    # lives in docs/, so a fixture must live there too.
    docs = source / "docs"
    docs.mkdir()

    (docs / "principle.md").write_text(
        "# Principle\n",
        encoding="utf-8",
    )


    output = tmp_path / "bundle.json"


    service = DefaultContextBundleService()


    bundle = service.generate(
        source,
        output,
        "commit123",
    )


    assert output.exists()

    assert bundle.source_commit == "commit123"

    assert len(bundle.artifacts) == 1
