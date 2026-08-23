from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).parents[3]

SCRIPT = ROOT / "scripts" / "sync_mirrors.sh"


def git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(cwd),
            "GIT_AUTHOR_NAME": "T",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "T",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
            "GIT_CONFIG_GLOBAL": str(cwd / ".gitconfig"),
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


def head_of(bare: Path) -> str | None:
    """The commit a bare repository's `main` points at, or `None`."""

    listed = subprocess.run(
        ["git", "ls-remote", str(bare), "refs/heads/main"],
        capture_output=True,
        text=True,
    )

    output = listed.stdout.strip()

    return output.split("\t")[0] if output else None


@pytest.fixture
def chain(tmp_path):
    """
    A SPOT, a clone, and two mirrors — real repositories on disk.

    STD-0002: every repository here lives under `tmp_path`. The
    script under test pushes, and pointing it at anything the
    project owns would publish from a test.

    The clone is the laptop, `origin` is Gitea, and `github` and
    `codeberg` are the two mirrors. Making one of them fail is
    then a matter of pointing its URL at nothing, which is what a
    rate-limited host looks like from here.
    """

    spot = tmp_path / "spot.git"
    github = tmp_path / "github.git"
    codeberg = tmp_path / "codeberg.git"
    work = tmp_path / "work"
    clone = tmp_path / "clone"

    for bare in (spot, github, codeberg):
        subprocess.run(
            ["git", "init", "--bare", "--initial-branch=main", str(bare)],
            check=True,
            capture_output=True,
        )

    work.mkdir()
    git("init", "--initial-branch=main", cwd=work)
    (work / "scripts").mkdir()
    (work / "scripts" / "sync_mirrors.sh").write_text(
        SCRIPT.read_text()
    )
    (work / "scripts" / "sync_mirrors.sh").chmod(0o755)
    (work / "README.md").write_text("# heritage\n")
    git("add", "-A", cwd=work)
    git("commit", "-m", "initial", cwd=work)
    git("remote", "add", "origin", str(spot), cwd=work)
    git("push", "origin", "main", cwd=work)

    subprocess.run(
        ["git", "clone", str(spot), str(clone)],
        check=True,
        capture_output=True,
    )
    git("remote", "add", "github", str(github), cwd=clone)
    git("remote", "add", "codeberg", str(codeberg), cwd=clone)

    return {
        "spot": spot,
        "github": github,
        "codeberg": codeberg,
        "work": work,
        "clone": clone,
    }


def run(clone: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(clone / "scripts" / "sync_mirrors.sh")],
        cwd=clone,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(clone),
            "GIT_CONFIG_GLOBAL": str(clone / ".gitconfig"),
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


def break_mirror(clone: Path, remote: str, tmp_path: Path) -> None:
    git(
        "remote",
        "set-url",
        remote,
        str(tmp_path / "does-not-exist.git"),
        cwd=clone,
    )


# --------------------------------------------------------------------
# The control case
# --------------------------------------------------------------------


def test_both_mirrors_receive_the_reference_branch(chain):

    result = run(chain["clone"])

    assert result.returncode == 0, result.stderr

    expected = head_of(chain["spot"])

    assert head_of(chain["github"]) == expected
    assert head_of(chain["codeberg"]) == expected


# --------------------------------------------------------------------
# GOV-0002/OS-009 — one mirror is not a dependency of another
# --------------------------------------------------------------------


def test_a_failing_first_mirror_does_not_prevent_the_second(
    chain, tmp_path
):
    """
    The occurrence, 2026-08-21: GitHub rate-limited the host,
    `set -e` ended the run at the first push, and Codeberg —
    reachable throughout — was never published. The mirror was
    left behind by a failure that had nothing to do with it.

    `github` is attempted first, so this is the ordering that
    used to lose Codeberg.
    """

    break_mirror(chain["clone"], "github", tmp_path)

    result = run(chain["clone"])

    assert head_of(chain["codeberg"]) == head_of(chain["spot"])
    assert head_of(chain["github"]) is None, result.stdout


def test_a_failing_second_mirror_does_not_undo_the_first(
    chain, tmp_path
):
    """
    The other direction, which the old script got right by
    accident of ordering rather than by design.
    """

    break_mirror(chain["clone"], "codeberg", tmp_path)

    run(chain["clone"])

    assert head_of(chain["github"]) == head_of(chain["spot"])


def test_the_run_fails_when_a_mirror_did(chain, tmp_path):
    """
    Publishing what it could is not the same as succeeding. A
    zero exit here would make a partial synchronization
    indistinguishable from a complete one to anything that reads
    exit codes — which is what a scheduled run does.
    """

    break_mirror(chain["clone"], "github", tmp_path)

    result = run(chain["clone"])

    assert result.returncode != 0


def test_the_run_names_the_mirror_that_did_not_receive_it(
    chain, tmp_path
):

    break_mirror(chain["clone"], "github", tmp_path)

    result = run(chain["clone"])

    assert "github" in result.stderr
    assert "1 of 2 mirror(s) did not receive it" in result.stderr


def test_a_complete_run_does_not_claim_to_be_incomplete(chain):

    result = run(chain["clone"])

    assert "Synchronization completed" in result.stdout
    assert "incomplete" not in result.stdout + result.stderr


def test_a_partial_run_does_not_claim_to_be_complete(
    chain, tmp_path
):
    """
    The sentence *Synchronization completed* was printed with the
    same satisfaction whatever had happened. A run that lost a
    mirror must not print it.
    """

    break_mirror(chain["clone"], "github", tmp_path)

    result = run(chain["clone"])

    assert "Synchronization completed" not in result.stdout


def test_an_unreachable_mirror_is_not_reported_as_published(
    chain, tmp_path
):
    """
    Found by writing the fix: running `publish` inside an `if`
    suspends `set -e` for everything it calls, so a failed
    `git push` no longer ended the function — it fell through to
    the lines that count commits and announce a publication.

    The guard against that is that every failure returns rather
    than raises, and this is what watches it.
    """

    break_mirror(chain["clone"], "github", tmp_path)

    result = run(chain["clone"])

    assert "published" not in result.stdout.split("codeberg")[0]


# --------------------------------------------------------------------
# GOV-0002/OS-010 — the script does not re-read itself mid-run
# --------------------------------------------------------------------


def test_a_pull_that_rewrites_the_script_does_not_change_this_run(
    chain,
):
    """
    The script pulls from the SPOT, and the SPOT holds the
    script. The run that delivers an improvement to
    `sync_mirrors.sh` rewrites the file bash is reading, and on
    2026-08-21 it printed the old message for exactly that
    reason.

    Here the SPOT carries a version whose last line echoes a
    marker. The running process must never print it: it had
    already parsed the whole file before the pull replaced it.
    And the file on disk must carry it afterwards, or the pull
    did not happen and this test proves nothing.

    **The dangerous case is not reproducible at this size.** Bash
    reads a file this small in one chunk, so an offset shift
    cannot be observed. What is observable is that the run is
    unaffected by the rewrite, and that is asserted rather than
    assumed.
    """

    work = chain["work"]
    script = work / "scripts" / "sync_mirrors.sh"

    script.write_text(
        script.read_text() + '\necho "THE-NEW-VERSION-SPOKE"\n'
    )

    git("add", "-A", cwd=work)
    git("commit", "-m", "improve the script", cwd=work)
    git("push", "origin", "main", cwd=work)

    result = run(chain["clone"])

    assert result.returncode == 0, result.stderr
    assert "THE-NEW-VERSION-SPOKE" not in result.stdout

    pulled = (chain["clone"] / "scripts" / "sync_mirrors.sh").read_text()

    assert "THE-NEW-VERSION-SPOKE" in pulled


def test_the_body_runs_only_from_the_final_invocation():
    """
    The structural property the guard rests on: everything the
    script does lives inside a function, and the only line that
    executes anything is the last one.

    Asserted on the file rather than on a run, because the defect
    it prevents cannot be reproduced at this size — and a guard
    that nothing watches is removed by the next person who finds
    it odd.
    """

    lines = [
        line
        for line in SCRIPT.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert lines[-1].startswith("main \"$@\"; exit")

    top_level = [
        line
        for line in lines
        if line == line.lstrip() and not line.endswith("{")
    ]

    assert top_level == [
        "set -euo pipefail",
        "}",
        "}",
        'main "$@"; exit $?',
    ]
