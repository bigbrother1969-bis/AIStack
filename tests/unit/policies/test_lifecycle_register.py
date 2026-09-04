from pathlib import Path

import pytest

from aistack.policies.lifecycle_register import (
    RegisterError,
    read_lifecycle_register,
)


def document(block: str) -> str:
    return (
        "# A governed document\n\n"
        "Prose is free everywhere but inside the block.\n\n"
        "```lifecycle\n" + block + "```\n\n"
        "More prose.\n"
    )


ONE = """artifact: OPS-0003
declarations:
  - container: frigate
    expected: intermittent
    reason: "Stopped most of the time to save resources."
"""


def test_the_declared_register_is_read():

    register = read_lifecycle_register(document(ONE))

    assert register.artifact == "OPS-0003"
    assert len(register.declarations) == 1
    assert register.declarations[0].container == "frigate"
    assert register.declarations[0].expected == "intermittent"


def test_a_yaml_block_elsewhere_is_not_the_register():
    """
    Same reasoning as `signatures`: a document explaining its own
    format will contain an illustrative block, and a parser taking
    the first fence found would eventually take the wrong one.
    """

    text = (
        "# Example\n\n"
        "```yaml\n"
        "artifact: NOT-THE-REGISTER\n"
        "declarations: []\n"
        "```\n\n" + document(ONE)
    )

    assert read_lifecycle_register(text).artifact == "OPS-0003"


def test_a_document_without_a_block_declares_no_register():

    with pytest.raises(RegisterError, match="no ```lifecycle block"):
        read_lifecycle_register("# Nothing here\n")


def test_two_blocks_are_refused():

    with pytest.raises(RegisterError, match="2 ```lifecycle blocks"):
        read_lifecycle_register(document(ONE) + document(ONE))


def test_invalid_yaml_names_itself():

    with pytest.raises(RegisterError, match="not valid YAML"):
        read_lifecycle_register(document("artifact: [unclosed\n"))


def test_an_unknown_top_level_key_is_refused():

    with pytest.raises(RegisterError, match="declaration"):
        read_lifecycle_register(
            document("artifact: OPS-0003\ndeclaration: []\n")
        )


def test_an_unknown_field_names_the_declaration_that_carries_it():

    block = ONE.replace(
        '    expected: intermittent',
        '    expected: intermittent\n    frequency: often',
    )

    with pytest.raises(RegisterError, match="declaration #1 of OPS-0003"):
        read_lifecycle_register(document(block))


def test_a_missing_reason_names_the_declaration():

    block = ONE.replace('    reason: "Stopped most of the time to save resources."\n', "")

    with pytest.raises(RegisterError) as raised:
        read_lifecycle_register(document(block))

    assert "declaration #1 of OPS-0003" in str(raised.value)
    assert "reason" in str(raised.value)


def test_an_unrecognised_expected_value_is_refused():

    block = ONE.replace("expected: intermittent", "expected: sometimes")

    with pytest.raises(RegisterError, match="declaration #1 of OPS-0003"):
        read_lifecycle_register(document(block))


def test_two_declarations_naming_the_same_container_are_refused():

    block = (
        "artifact: OPS-0003\n"
        "declarations:\n"
        "  - container: frigate\n"
        "    expected: intermittent\n"
        "    reason: \"a\"\n"
        "  - container: frigate\n"
        "    expected: continuous\n"
        "    reason: \"b\"\n"
    )

    with pytest.raises(RegisterError, match="frigate is declared twice"):
        read_lifecycle_register(document(block))


def test_an_empty_register_is_readable():
    """
    A register that declares nothing yet is a state, not an error
    — the same reading `SignatureCatalogue` gives an empty
    catalogue.
    """

    register = read_lifecycle_register(
        document("artifact: OPS-0003\ndeclarations: []\n")
    )

    assert register.declarations == ()
    assert register.for_container("frigate") is None


# --------------------------------------------------------------------
# The governed document itself
# --------------------------------------------------------------------


OPS_0003 = (
    Path(__file__).parents[3]
    / "docs"
    / "04-development"
    / "OPS-0003-Container-Lifecycle-Declarations.md"
)


def test_the_governed_register_reads():
    """
    Same reasoning as `test_the_governed_catalogue_reads`: a
    fixture that drifted from the artifact would prove the parser
    works on text nobody ships.
    """

    register = read_lifecycle_register(OPS_0003.read_text(encoding="utf-8"))

    assert register.artifact == "OPS-0003"
    assert [d.container for d in register.declarations] == ["frigate"]


def test_the_governed_register_declares_frigate_intermittent():

    register = read_lifecycle_register(OPS_0003.read_text(encoding="utf-8"))

    declaration = register.for_container("frigate")

    assert declaration is not None
    assert declaration.expected == "intermittent"
    assert declaration.reason.strip() != ""
