from pathlib import Path
import re
import subprocess

import pytest


ROOT = Path(__file__).parents[3]

DOCS = ROOT / "docs"

FRONTMATTER = re.compile(r"^---\n(.*?)\n---", re.S)

UPDATED = re.compile(r"^\s*updated:\s*(\S+)\s*$", re.M)

# A commit that added or removed a `version:` line changed the
# artifact's version, which is what makes an edit a revision.
VERSION_LINE = r"^\s*version:"


def declared_update(path: Path) -> str | None:
    """The `updated:` an artifact declares, or `None`."""

    block = FRONTMATTER.match(path.read_text())

    if not block:
        return None

    found = UPDATED.search(block.group(1))

    return found.group(1) if found else None


def last_revision(path: Path, root: Path = ROOT) -> str | None:
    """
    The author date of the last commit that changed the version.

    **Author date, not committer date.** `git format-patch` carries
    the author date and `git am` preserves it, so on both the
    agent's clone and the owner's workstation it means the same
    thing: when the artifact was written. The committer date means
    when the patch was applied, which is a different fact and would
    fire on every normal delivery.

    `--follow` matters. Without it a rename reads as the whole file
    being added, so `ADR-0003` — renamed 2026-08-23 without being
    revised — reported a revision it never had.
    """

    result = subprocess.run(
        [
            "git", "log", "-1",
            "--format=%ad", "--date=short",
            "-G", VERSION_LINE,
            "--follow",
            "--", str(path),
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip() or None


def artifacts() -> list[Path]:
    return sorted(
        path
        for path in DOCS.rglob("*.md")
        if declared_update(path) is not None
    )


def test_no_artifact_claims_to_predate_its_own_revision():
    """
    An artifact whose `updated:` precedes the commit that changed
    its version is stating a date that was already false when it
    was written. GOV-0002/OS-029.

    The occurrence: OPS-0002 was written on 2026-08-27 and dated
    2026-08-23 throughout — seventeen wrong dates in one patch, in
    a C2 artifact and a C2 register, published to the SPOT and both
    mirrors before a human noticed. The agent had carried the date
    from a conversation record instead of reading a clock.

    **The rule is narrowed to revisions on purpose.** Comparing
    `updated:` with the last commit to touch a file at all reports
    31 of 65 artifacts, because mechanical sweeps — a renumbering,
    a citation corrected across the tree — touch files without
    revising them. Measured 2026-08-27, both ways. A rule that
    accuses half of what it governs is not describing it, which is
    what retired the file-name rule four patches earlier.

    Bumping the version is what says an edit was a revision. Under
    that reading the heritage held one exception, and it was real:
    `eb43842` moved ENG-TEST-0001 from 1.0 to 1.1 on 2026-08-21 and
    left `updated: 2026-07-24`.
    """

    stale = []

    for path in artifacts():

        declared = declared_update(path)
        revised = last_revision(path)

        if revised is None:
            continue

        if declared < revised:
            stale.append(
                f"{path.relative_to(ROOT)}: declares {declared}, "
                f"revised {revised}"
            )

    assert stale == [], stale


def test_the_comparison_reaches_the_history():
    """
    The test above passes on a repository with no history: every
    artifact reports no revision, every comparison is skipped, and
    nothing is verified.

    So the floor is stated. 65 artifacts declare an `updated:` and
    all 65 have a commit that changed their version, measured
    2026-08-27. A shallow clone or an export without `.git` fails
    here rather than passing silently — which is the shape of the
    test that passed on a fresh clone while verifying nothing,
    found 2026-08-23.
    """

    declaring = artifacts()

    assert len(declaring) >= 65

    revised = [path for path in declaring if last_revision(path)]

    assert len(revised) == len(declaring), [
        str(p.relative_to(ROOT)) for p in declaring if not last_revision(p)
    ]


@pytest.mark.parametrize(
    "declared, revised, stale",
    [
        ("2026-08-23", "2026-08-27", True),
        ("2026-08-27", "2026-08-27", False),
        ("2026-08-27", "2026-08-23", False),
    ],
)
def test_only_a_date_behind_its_revision_is_stale(declared, revised, stale):
    """
    The comparison itself, stated rather than implied.

    A date *after* the last revision is not a defect: an artifact
    edited without a version bump — a typo, a citation corrected —
    may legitimately carry a later `updated:` than its last
    revision. `FDN-0009` is that case, and an equality rule would
    have accused it.
    """

    assert (declared < revised) is stale


def test_the_author_date_is_read_and_not_the_committer_date():
    """
    Found by mutation, and only constructible: every commit in the
    agent's clone was authored and committed in the same second, so
    swapping `%ad` for `%cd` changed nothing there.

    It changes everything on the workstation. `git format-patch`
    carries the author date and `git am` preserves it while setting
    a fresh committer date, so the committer date is *when the
    patch was applied* — later than the artifact was written, on
    every single delivery this project makes. Reading it would make
    the test fire on correct work and stay silent on the defect it
    exists for.

    So a repository is built where the two differ by five months.
    """

    import os
    import tempfile

    with tempfile.TemporaryDirectory() as directory:

        root = Path(directory)
        document = root / "artifact.md"

        document.write_text(
            "---\nartifact:\n  id: X\n  version: 1.0\n"
            "  updated: 2026-01-01\n---\n"
        )

        environment = {
            **os.environ,
            "GIT_AUTHOR_DATE": "2026-01-01T09:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-06-01T09:00:00+00:00",
            "GIT_AUTHOR_NAME": "T",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "T",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
            "GIT_CONFIG_GLOBAL": str(root / ".gitconfig"),
            "GIT_CONFIG_SYSTEM": "/dev/null",
        }

        for command in (
            ["init", "--initial-branch=main", "."],
            ["add", "artifact.md"],
            ["commit", "-m", "the artifact"],
        ):
            subprocess.run(
                ["git", *command],
                cwd=root,
                env=environment,
                check=True,
                capture_output=True,
            )

        assert last_revision(document, root=root) == "2026-01-01"
