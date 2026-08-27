from pathlib import Path
import re
import subprocess


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


# --------------------------------------------------------------------
# Sourcing twice leaves the same environment as sourcing once
# --------------------------------------------------------------------


def sourced_environment(
    command: str,
    variable: str,
    times: int,
    initial: str | None = None,
) -> list[str]:
    """
    The value of `variable` after sourcing `command` `times` over.

    Run in a real shell, because the defect is a shell defect. A
    test that read the file and reasoned about it would have
    agreed with the file's author.

    `initial` seeds the variable before the first source. Without
    it every run starts from an empty `PYTHONPATH`, and de-
    duplication that kept the first occurrence rather than the
    last is indistinguishable from one that kept the last — found
    by mutation, on the assertion written to catch exactly that.
    """

    script = (
        "".join(f"source {command} >/dev/null 2>&1; " for _ in range(times))
        + f'printf "%s" "${variable}"'
    )

    environment = {"PATH": "/usr/bin:/bin", "HOME": str(ROOT)}

    if initial is not None:
        environment[variable] = initial

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )

    return [entry for entry in result.stdout.split(":") if entry]


def test_sourcing_the_declaration_twice_declares_the_roots_once():
    """
    It prepended unconditionally until 2026-08-23, so every source
    added the two roots again — six copies of each were visible in
    one working session.

    Found because ENG-TEST-0002 v2.2 made `scripts/dev-env.sh` the
    governed command and that file prints `PYTHONPATH`. The report
    the principle now names is what exposed it.

    Harmless to imports, and not harmless to the promise: this
    principle is C3 and asks for *deterministic execution*. A
    variable whose value depends on how many times you sourced the
    source of truth is not deterministic. GOV-0002/OS-026.
    """

    once = sourced_environment("bin/aistack_env.sh", "PYTHONPATH", 1)
    twice = sourced_environment("bin/aistack_env.sh", "PYTHONPATH", 2)

    assert once == twice
    assert len(once) == len(set(once))


def test_sourcing_the_provider_twice_puts_the_venv_on_path_once():

    once = sourced_environment(
        "scripts/dev-env.sh", "PATH", 1, initial="/usr/bin:/bin"
    )
    thrice = sourced_environment(
        "scripts/dev-env.sh", "PATH", 3, initial="/usr/bin:/bin"
    )

    assert once == thrice

    venv = str(ROOT / ".venv" / "bin")

    assert once.count(venv) <= 1


def test_the_declared_roots_come_first_and_stay_first():
    """
    Order is the half that matters. A developer with two checkouts
    who sources one then the other must import from the second,
    and de-duplication that kept the *first* occurrence would give
    them the first.
    """

    entries = sourced_environment(
        "bin/aistack_env.sh",
        "PYTHONPATH",
        2,
        initial="/somewhere/else",
    )

    assert entries[:2] == [str(ROOT / "src"), str(ROOT)]
    assert "/somewhere/else" in entries


def test_the_declaration_forbids_compiled_bytecode():
    """
    `Dockerfile` has set `PYTHONDONTWRITEBYTECODE` since the image
    existed; `bin/aistack_env.sh` did not until 2026-08-27, so a
    developer and an image ran Python two different ways.
    ENG-TEST-0002 is C3 and asks for *portability across
    environments*.

    The cost was measured, and it is not the disk. A mutation pass
    rewrites a module and re-runs the suite in under a second —
    faster than the filesystem timestamp resolution CPython uses to
    decide whether its cached bytecode is stale. Two tests failed
    against source that was already correct.

    It defeats the method in the other direction too: a mutation
    can appear to survive when it was never executed, and a
    surviving mutation is read here as an invariant nobody
    watches. GOV-0002/OS-033.
    """

    assert "PYTHONDONTWRITEBYTECODE=1" in DECLARATION.read_text()


def test_the_images_and_the_declaration_agree_on_bytecode():
    """
    Two projections of one decision, and the check is the same
    shape as the one comparing the declared interpreter with what
    the images ship.
    """

    image = (ROOT / "Dockerfile").read_text()

    assert "PYTHONDONTWRITEBYTECODE=1" in image
