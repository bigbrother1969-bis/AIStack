from pathlib import Path
import shutil

from aistack.context_bundle.discovery.markdown_discovery import (
    MarkdownDiscovery,
)


ROOT = Path(__file__).parents[3]


def test_no_source_names_the_machine_it_was_generated_on(projection):
    """
    `GOV-0002/OS-096`: every artifact of the projection says where
    it is in the heritage, relative to its root, and none says where
    the heritage happened to be when the bundle was generated.

    Before, all 65 carried an absolute path — `/srv/aistack/...` on
    the server, `/home/...` on a workstation — in a field that no
    hash covered and that ten checks read.

    Measured 2026-11-18 on `main`: 65 artifacts, none absolute. The
    floor is the count, so that a projection that came back empty
    is not read as one that names nothing.
    """

    assert len(projection.artifacts) >= 65

    absolute = [
        artifact.source
        for artifact in projection.artifacts
        if artifact.source.startswith("/")
        or artifact.source[1:3] == ":\\"
    ]

    assert absolute == [], absolute[:5]

    assert not any(
        str(ROOT) in artifact.source for artifact in projection.artifacts
    )


def test_the_heritage_generated_elsewhere_carries_the_same_sources(
    projection, tmp_path
):
    """
    The same heritage, copied to another directory and generated
    there, carries the same sources: the bundle no longer depends on
    where it was made. Constructed, because the field was the one
    thing two generations could not share.

    Only the documents are copied — the rest of the repository is
    read by the export through `ROOT` — so what is compared is the
    set of sources of the artifacts the copy holds, against the same
    documents in the projection.
    """

    elsewhere = tmp_path / "somewhere-else" / "heritage"

    shutil.copytree(ROOT / "docs", elsewhere / "docs")

    copied = {
        result.path.as_posix()
        for result in MarkdownDiscovery().discover(elsewhere)
    }

    held = {
        artifact.source
        for artifact in projection.artifacts
        if artifact.source.startswith("docs/")
    }

    assert held <= copied, sorted(held - copied)
    assert all(not source.startswith("/") for source in copied)
