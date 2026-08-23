from pathlib import Path
import re


ROOT = Path(__file__).parents[2]

PRINCIPLE = (
    ROOT
    / "docs"
    / "00-foundation"
    / "ENG-TEST-0002-Declared-Execution-Environment-Principle.md"
)

README = ROOT / "README.md"

PROVIDER = ROOT / "scripts" / "dev-env.sh"

DECLARATION = ROOT / "bin" / "aistack_env.sh"


# A shell instruction, not the phrase "source roots" — which both
# documents use, and which a looser pattern reads as a command to
# source a file named `roots`.
SOURCED = re.compile(r"^\s*source\s+(\S+/\S+\.sh)\s*$", re.M)


def sourced_by(document: Path) -> set[str]:
    """
    Every path a document tells a reader to `source`.

    Read from the prose, because the prose is the instruction. A
    developer types what the artifact shows them, and until
    2026-08-23 what ENG-TEST-0002 showed them was a file that
    declares the environment without providing it.
    """

    return set(SOURCED.findall(document.read_text()))


def test_the_principle_names_the_file_that_provides_the_environment():
    """
    ENG-TEST-0002 is C3. The command it prints is the command
    people run.

    It printed `source bin/aistack_env.sh` until 2026-08-23. That
    file declares the two source roots and the interpreter the
    heritage is verified on, and provides neither: `python3` stays
    whatever the distribution installed — 3.12 on Linux Mint 22.3
    — while `pyproject.toml` requires 3.13 and both images ship
    `python:3.13-slim`.

    The owner ran it exactly as written on a bare shell: 514
    passed and the interpreter test failed. GOV-0002/OS-025.
    """

    assert "scripts/dev-env.sh" in sourced_by(PRINCIPLE)


def test_the_readme_and_the_principle_show_the_same_command():
    """
    They have drifted before, and expensively. ENG-TEST-0002 v1.0
    asked for `PYTHONPATH=src`, `bin/aistack_env.sh` exported the
    repository root, and `scripts/dev-env.sh` exported `src` — one
    knowledge item with three declarations, none of them complete,
    which is what FDN-P-005 forbids and what v2.0 was written to
    end.

    Nothing compared them then. This does.
    """

    assert sourced_by(README) == sourced_by(PRINCIPLE)


def test_the_provider_sources_the_declaration():
    """
    The reason declaring and providing may stay two files without
    giving the environment two SPOTs: the provider does not
    restate the declaration, it sources it.

    If this ever stopped being true, `scripts/dev-env.sh` would
    become a second, silent declaration of the same knowledge —
    exactly the state ENG-TEST-0002 v2.0 was written to end.
    """

    assert "bin/aistack_env.sh" in PROVIDER.read_text()

    body = PROVIDER.read_text()

    assert "PYTHONPATH" not in body.split("source")[0]


def test_the_declaration_provides_nothing():
    """
    The other direction, and it is the one that keeps the split
    honest. ADR-0001 makes `bin/aistack_env.sh` the source of
    truth for the environment; a source of truth that also
    mutates the caller's PATH to satisfy itself is no longer a
    declaration.

    Asserted so that the next person who finds the two-file split
    inconvenient learns from a red suite that it is deliberate.
    """

    body = DECLARATION.read_text()

    assert ".venv" not in body
    assert "PATH=" not in body.replace("PYTHONPATH=", "")
