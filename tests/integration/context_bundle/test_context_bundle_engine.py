from pathlib import Path

from aistack.context_bundle.engine import (
    DefaultContextBundleEngine,
)


def test_context_bundle_engine_builds_complete_bundle(
    tmp_path,
):

    source = tmp_path / "knowledge"

    source.mkdir()

    (source / "principle.md").write_text(
        "# Principle\n",
        encoding="utf-8",
    )

    output = tmp_path / "bundle.json"


    engine = DefaultContextBundleEngine()


    bundle = engine.build(
        source,
        output,
        "commit123",
    )


    assert output.exists()

    assert bundle.source_commit == "commit123"

    assert len(bundle.artifacts) == 1

    assert (
        bundle.artifacts[0].content
        == "# Principle\n"
    )
