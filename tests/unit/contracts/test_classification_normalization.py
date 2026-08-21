import pytest

from aistack.contracts.classification import (
    KnowledgeDomain,
    SemanticType,
    normalize_domain,
    normalize_semantic_type,
)
from aistack.contracts.undeclared import UNDECLARED


@pytest.mark.parametrize("member", list(KnowledgeDomain))
def test_every_governed_domain_survives_normalization(member):

    assert normalize_domain(member.value) == member.value


@pytest.mark.parametrize("member", list(SemanticType))
def test_every_governed_semantic_type_survives_normalization(member):

    assert normalize_semantic_type(member.value) == member.value


@pytest.mark.parametrize(
    "written, expected",
    [
        ("foundation", "Foundation"),
        ("  Standards  ", "Standards"),
        ("KNOWLEDGE ASSETS", "Knowledge Assets"),
    ],
)
def test_case_and_whitespace_do_not_change_the_declaration(
    written,
    expected,
):
    """
    A human writing "foundation" means Foundation. Canonical
    form is a presentation concern, not a qualification.
    """

    assert normalize_domain(written) == expected


@pytest.mark.parametrize("value", [None, "", "   "])
def test_an_absent_declaration_is_undeclared(value):

    assert normalize_domain(value) == UNDECLARED
    assert normalize_semantic_type(value) == UNDECLARED


@pytest.mark.parametrize(
    "value",
    [
        "Foundation Document",
        "Component README",
        "Foundation Manifesto",
        "System Specification",
    ],
)
def test_a_value_outside_the_vocabulary_is_undeclared(value):
    """
    These four are real labels from the heritage. They are
    legitimate `type` values and they are **not** semantic
    types.

    Nothing maps them to the nearest plausible member —
    "System Specification" does not silently become
    "Specification". A closed vocabulary that accepts anything
    is not a vocabulary, and guessing here would be the machine
    qualifying on the human's behalf (FDN-0003 Article 4).
    """

    assert normalize_semantic_type(value) == UNDECLARED


def test_normalization_does_not_consult_anything_but_the_value():
    """
    No path, no filename, no content heuristic — the rule
    STD-0100 v2.0 states in writing.
    """

    assert normalize_domain("docs/00-foundation/x.md") == UNDECLARED
    assert normalize_semantic_type("adr/ADR-0001.md") == UNDECLARED

    # ...while the declaration itself is read, wherever it came from.
    assert normalize_semantic_type("ADR") == "ADR"
