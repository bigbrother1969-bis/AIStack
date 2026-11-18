
from aistack.context_bundle.discovery.markdown_discovery import (
    MarkdownDiscovery,
)


def test_markdown_discovery_reads_markdown_files(tmp_path):

    # Eligibility is an allow list: the governed heritage lives
    # in docs/, so a fixture must live there too.
    (tmp_path / "docs").mkdir()

    file = tmp_path / "docs" / "test.md"
    file.write_text(
        "# Test",
        encoding="utf-8",
    )

    discovery = MarkdownDiscovery()

    results = discovery.discover(tmp_path)

    assert len(results) == 1
    assert results[0].content == "# Test"


def test_markdown_discovery_ignores_non_markdown(tmp_path):

    file = tmp_path / "test.txt"
    file.write_text(
        "ignored",
        encoding="utf-8",
    )

    discovery = MarkdownDiscovery()

    results = discovery.discover(tmp_path)

    assert results == []


def test_markdown_discovery_generates_hash(tmp_path):

    (tmp_path / "docs").mkdir()

    file = tmp_path / "docs" / "test.md"
    file.write_text(
        "# Test",
        encoding="utf-8",
    )

    discovery = MarkdownDiscovery()

    result = discovery.discover(tmp_path)[0]

    assert len(result.content_hash) == 64

def test_discovery_ignores_generated_bundles(tmp_path):

    bundles = (
        tmp_path
        / "context"
        / "bundles"
    )

    bundles.mkdir(
        parents=True
    )

    (bundles / "bundle.md").write_text(
        "# Generated Bundle",
        encoding="utf-8",
    )


    discovery = MarkdownDiscovery()

    results = discovery.discover(
        tmp_path
    )

    assert results == []

def test_discovery_ignores_non_source_areas(tmp_path):

    excluded = [
        "context/bundles",
        "inbox",
        ".pytest_cache",
    ]

    for directory in excluded:

        path = (
            tmp_path
            / directory
        )

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        (path / "duplicate.md").write_text(
            "# Duplicate",
            encoding="utf-8",
        )


    discovery = MarkdownDiscovery()

    results = discovery.discover(
        tmp_path
    )

    assert results == []


def test_the_path_is_relative_to_the_root_it_was_given(tmp_path):
    """
    `GOV-0002/OS-096`: the discovery reports where a file is in
    the heritage, never where the heritage was when it was read.
    """

    (tmp_path / "docs" / "00-foundation").mkdir(parents=True)

    (tmp_path / "docs" / "00-foundation" / "a.md").write_text(
        "# A",
        encoding="utf-8",
    )

    results = MarkdownDiscovery().discover(tmp_path)

    assert [str(result.path) for result in results] == [
        "docs/00-foundation/a.md"
    ]

    assert not results[0].path.is_absolute()
    assert str(tmp_path) not in str(results[0].path)
