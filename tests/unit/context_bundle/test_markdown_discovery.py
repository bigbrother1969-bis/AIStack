from pathlib import Path

from aistack.context_bundle.discovery.markdown_discovery import (
    MarkdownDiscovery,
)


def test_markdown_discovery_reads_markdown_files(tmp_path):

    file = tmp_path / "test.md"
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

    file = tmp_path / "test.md"
    file.write_text(
        "# Test",
        encoding="utf-8",
    )

    discovery = MarkdownDiscovery()

    result = discovery.discover(tmp_path)[0]

    assert len(result.content_hash) == 64
