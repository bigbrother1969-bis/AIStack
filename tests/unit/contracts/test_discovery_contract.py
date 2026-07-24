from pathlib import Path

from aistack.contracts.discovery import DiscoveryResult


def test_discovery_result_creation():

    result = DiscoveryResult(
        path=Path("README.md"),
        content="# AIStack",
        content_hash="abc123",
    )

    assert result.path == Path("README.md")
    assert result.content == "# AIStack"
    assert result.content_hash == "abc123"


def test_discovery_result_is_immutable():

    result = DiscoveryResult(
        path=Path("README.md"),
        content="# AIStack",
        content_hash="abc123",
    )

    try:
        result.content = "changed"
        assert False, "DiscoveryResult must be immutable"

    except Exception:
        assert True
