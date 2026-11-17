from aistack.context_bundle.builders.frontmatter import (
    declared_value,
    parse_artifact_frontmatter,
)


DECLARED = """---
artifact:
  id: FDN-0009
  title: AI Collaboration Protocol
  owner: Foundation
  status: Proposed
---

# Body
"""


def test_declared_frontmatter_is_read():

    declared = parse_artifact_frontmatter(DECLARED)

    assert declared["id"] == "FDN-0009"
    assert declared["owner"] == "Foundation"
    assert declared["status"] == "Proposed"


def test_absent_frontmatter_yields_nothing():

    assert parse_artifact_frontmatter("# Just a title\n") == {}


def test_unterminated_frontmatter_yields_nothing():
    """
    The AIStack README carried an unterminated frontmatter for
    fourteen commits. Such a file must produce no metadata at
    all rather than a partial guess.
    """

    content = "---\nartifact:\n  id: BROKEN\n\n# Body\n"

    assert parse_artifact_frontmatter(content) == {}


def test_malformed_yaml_yields_nothing():

    content = "---\nartifact:\n  id: [unclosed\n---\n"

    assert parse_artifact_frontmatter(content) == {}


def test_frontmatter_without_artifact_key_yields_nothing():

    content = "---\ntitle: not an artifact block\n---\n"

    assert parse_artifact_frontmatter(content) == {}


def test_declared_value_returns_the_declaration():

    assert declared_value({"status": "Published"}, "status") == "Published"


def test_undeclared_value_is_reported_unknown():
    """
    Article 12: an absent value is a governed state and must
    stay visible. It is never replaced by a plausible default.
    """

    assert declared_value({}, "status") == "unknown"


def test_empty_declaration_is_reported_unknown():

    assert declared_value({"status": "   "}, "status") == "unknown"
