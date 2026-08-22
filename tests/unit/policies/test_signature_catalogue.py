from pathlib import Path

import pytest

from aistack.contracts.undeclared import UNDECLARED
from aistack.policies.signature_catalogue import (
    CatalogueError,
    read_signature_catalogue,
)


def document(block: str) -> str:
    return (
        "# A governed document\n\n"
        "Prose is free everywhere but inside the block.\n\n"
        "```signatures\n" + block + "```\n\n"
        "More prose.\n"
    )


ONE = """artifact: OPS-0001
signatures:
  - identifier: OPS-0001/S-001
    pattern: "AUTH_FAILED"
    case_sensitive: true
    interpretation: "OpenVPN reports an AUTH_FAILED error."
    remediation: "Check the VPN credentials the container uses."
    depth: 100
    confidence: Declared
    grounding: unknown
"""


def test_the_declared_catalogue_is_read():

    catalogue = read_signature_catalogue(document(ONE))

    assert catalogue.artifact == "OPS-0001"
    assert len(catalogue.signatures) == 1
    assert catalogue.signatures[0].identifier == "OPS-0001/S-001"
    assert catalogue.signatures[0].grounding == UNDECLARED


def test_a_yaml_block_elsewhere_is_not_the_catalogue():
    """
    The tag is `signatures` and not `yaml` precisely because a
    document explaining its own format will contain an
    illustrative block. Taking the first fence would eventually
    take the wrong one.
    """

    text = (
        "# Example\n\n"
        "```yaml\n"
        "artifact: NOT-THE-CATALOGUE\n"
        "signatures: []\n"
        "```\n\n" + document(ONE)
    )

    assert read_signature_catalogue(text).artifact == "OPS-0001"


def test_a_document_without_a_block_declares_no_catalogue():

    with pytest.raises(CatalogueError, match="no ```signatures block"):
        read_signature_catalogue("# Nothing here\n")


def test_two_blocks_are_refused():
    """
    Two catalogues in one document, and no way to say which
    governs.
    """

    with pytest.raises(CatalogueError, match="2 ```signatures blocks"):
        read_signature_catalogue(document(ONE) + document(ONE))


def test_invalid_yaml_names_itself():

    with pytest.raises(CatalogueError, match="not valid YAML"):
        read_signature_catalogue(document("artifact: [unclosed\n"))


def test_an_unknown_top_level_key_is_refused():

    with pytest.raises(CatalogueError, match="signatues"):
        read_signature_catalogue(
            document("artifact: OPS-0001\nsignatues: []\n")
        )


def test_an_unknown_field_names_the_signature_that_carries_it():
    """
    A typo in a field name would otherwise be dropped in silence
    and the signature would run with a default it never declared.
    """

    block = ONE.replace("    depth: 100", "    dept: 100\n    depth: 100")

    with pytest.raises(CatalogueError, match="signature #1 of OPS-0001"):
        read_signature_catalogue(document(block))


def test_a_missing_field_names_the_signature_and_the_field():

    block = ONE.replace("    case_sensitive: true\n", "")

    with pytest.raises(CatalogueError) as raised:
        read_signature_catalogue(document(block))

    assert "signature #1 of OPS-0001" in str(raised.value)
    assert "case_sensitive" in str(raised.value)


def test_a_refused_value_names_the_signature():

    block = ONE.replace("    depth: 100", "    depth: 0")

    with pytest.raises(CatalogueError, match="signature #1 of OPS-0001"):
        read_signature_catalogue(document(block))


def test_an_empty_catalogue_is_readable():
    """
    A register that declares nothing yet is a state, not an
    error. It reads, and `deepest` is zero.
    """

    catalogue = read_signature_catalogue(
        document("artifact: OPS-0001\nsignatures: []\n")
    )

    assert catalogue.signatures == ()
    assert catalogue.deepest == 0


# --------------------------------------------------------------------
# The governed document itself
# --------------------------------------------------------------------


OPS_0001 = (
    Path(__file__).parents[3]
    / "docs"
    / "04-development"
    / "OPS-0001-Container-Log-Signatures.md"
)


def test_the_governed_catalogue_reads():
    """
    ADR-0009 § 4: the same parser runs at projection and at
    runtime. This test is the third caller, and it reads the real
    document rather than a fixture — a fixture that drifted from
    the artifact would prove the parser works on text nobody
    ships.
    """

    catalogue = read_signature_catalogue(
        OPS_0001.read_text(encoding="utf-8")
    )

    assert catalogue.artifact == "OPS-0001"
    assert [s.identifier for s in catalogue.signatures] == [
        "OPS-0001/S-001",
        "OPS-0001/S-002",
        "OPS-0001/S-003",
        "OPS-0001/S-004",
    ]
    assert catalogue.deepest == 100


def test_the_governed_catalogue_declares_one_case_insensitive_rule():
    """
    `S-004` is the only one, and it is the only one the
    experimenter compared against `logs.lower()`. Whether that
    was a decision or an accident is recorded in the document as
    undecided; this test states the fact so a change to it is
    deliberate.
    """

    catalogue = read_signature_catalogue(
        OPS_0001.read_text(encoding="utf-8")
    )

    insensitive = [
        s.identifier for s in catalogue.signatures if not s.case_sensitive
    ]

    assert insensitive == ["OPS-0001/S-004"]


def test_every_governed_signature_declares_its_grounding_as_unknown():
    """
    Recorded as the state of 2026-08-22. When a grounding is
    written, this test fails and says so — which is the point: a
    remediation acquiring a policy is a governed change, not a
    silent improvement.
    """

    catalogue = read_signature_catalogue(
        OPS_0001.read_text(encoding="utf-8")
    )

    assert {s.grounding for s in catalogue.signatures} == {UNDECLARED}
