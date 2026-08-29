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


def declared_interpreter() -> str:
    """
    The interpreter version the declaration names, read from it.

    Read rather than restated: a test that hardcoded "3.13" would
    be a second declaration of the knowledge ADR-0001 puts in one
    file, which is what FDN-P-005 forbids.
    """

    found = re.search(
        r'^AISTACK_PYTHON_REQUIRED="([^"]+)"', DECLARATION.read_text(), re.M
    )

    assert found, "the declaration names no interpreter"

    return found.group(1)


def sourced_interpreter(command: str) -> tuple[str, str]:
    """
    What sourcing `command` warns, and which `python3` it leaves.

    Both from one real shell, because the defect is the distance
    between the two. Reading the files and reasoning about them is
    exactly what agreed with their author for six days.
    """

    script = (
        f"source {command} >/dev/null; "
        "python3 -c 'import sys; print(f\"{sys.version_info.major}."
        "{sys.version_info.minor}\")' 2>/dev/null"
    )

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(ROOT)},
    )

    return result.stderr, result.stdout.strip()


def test_the_provider_warns_about_the_interpreter_it_provides():
    """
    The command ENG-TEST-0002 prints must describe the interpreter
    that command runs — not the one it found on the way in.

    Until 2026-08-29 `bin/aistack_env.sh` verified at source time
    and `scripts/dev-env.sh` changed the interpreter afterwards.
    Measured on the owner's laptop in a bare shell: the first
    source warned "python3 is 3.12", the second was silent, and
    `python3 --version` printed 3.13.15. The suite had been
    running on the declared interpreter throughout, and the false
    reading had been copied into the boot report as a residual.

    The assertion is an equivalence, so it stays honest on a
    machine whose distribution already ships the declared
    interpreter: there it holds because both halves are true, and
    it is on every other machine that it bites.
    """

    warning, interpreter = sourced_interpreter("scripts/dev-env.sh")

    assert (interpreter == declared_interpreter()) is (
        "verified on" not in warning
    )


def test_the_declaration_warns_about_the_interpreter_the_launchers_run():
    """
    The other half, and it is why the check stayed in the
    declaration rather than moving to the provider.

    The three launchers beside `bin/aistack_env.sh` source it and
    immediately run `python3 -m …` without touching the search
    path. For them the interpreter measured at source time is the
    one that executes, and the warning was never wrong. Deferring
    it unconditionally would have taken a correct warning away
    from `run_selection_ui.sh` to fix a wrong one elsewhere.
    """

    warning, interpreter = sourced_interpreter("bin/aistack_env.sh")

    assert (interpreter == declared_interpreter()) is (
        "verified on" not in warning
    )


def test_the_provider_pays_the_check_it_defers(tmp_path):
    """
    Deferring and never calling is silence, and silence is exactly
    what the warning exists to prevent.

    The equivalence asserted above cannot see this: on a machine
    whose provider does deliver the declared interpreter, a
    provider that warns about nothing and a provider that checks
    nothing are indistinguishable. Found by mutation — removing
    the call left the suite green.

    So the situation is built rather than waited for: the two
    scripts in a tree with no virtual environment, and an
    interpreter on the search path that is certainly not the
    declared one. There the provider has nothing to put ahead of
    it, and it must say so.
    """

    (tmp_path / "bin").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "bin" / "aistack_env.sh").write_text(DECLARATION.read_text())
    (tmp_path / "scripts" / "dev-env.sh").write_text(PROVIDER.read_text())

    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "python3").write_text('#!/bin/sh\nprintf "0.0\\n"\n')
    (stub / "python3").chmod(0o755)

    result = subprocess.run(
        ["bash", "-c", "source scripts/dev-env.sh >/dev/null"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PATH": f"{stub}:/usr/bin:/bin", "HOME": str(tmp_path)},
    )

    assert "verified on" in result.stderr
    assert "0.0" in result.stderr


def test_the_images_and_the_declaration_agree_on_bytecode():
    """
    Two projections of one decision, and the check is the same
    shape as the one comparing the declared interpreter with what
    the images ship.
    """

    image = (ROOT / "Dockerfile").read_text()

    assert "PYTHONDONTWRITEBYTECODE=1" in image
