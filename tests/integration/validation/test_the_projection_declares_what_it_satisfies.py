from pathlib import Path

from aistack.integrity.checks.false_declarations import (
    FalseDeclarationCheck,
)


ROOT = Path(__file__).parents[3]


def test_no_class_declares_a_contract_it_does_not_satisfy(projection):
    """
    GOV-0002/OS-040: a class naming an ABC or a Protocol as a base
    provides what that base declares.

    Python does not enforce it. The ABC machinery checks that a
    method of the right *name* exists and never looks at its
    signature, so `SshBundleTransfer` carried a false declaration
    from the day it was written until 2026-08-27, and a second one
    — one parameter name — until 2026-08-28.

    **The check publishes the count; this fails the suite.** Both
    were decided on 2026-08-28 by the owner, and they do different
    work: `false-declarations` states the condition of any
    projection, including one produced elsewhere or by an older
    pipeline, while this asserts that *this repository* holds
    none. A published figure nobody is obliged to act on is how
    the previous divergence lasted weeks.
    """

    findings = FalseDeclarationCheck().evaluate(projection)

    assert findings == [], [f.subjects for f in findings]


def test_the_rule_is_measured_over_a_heritage_that_can_break_it(
    projection,
):
    """
    The test above passes on a projection carrying no inventory,
    on one whose declarations were never measured, and on a
    heritage where no class declares anything. Each of those is a
    silent instrument, and from the report they look identical to
    a clean one.

    So this states what was actually measured: **40
    class-contract declarations over 154 concrete classes on
    2026-08-28**, of which one was false and is repaired in the
    same series. The figures are floors, not equalities — the
    heritage is meant to grow, and a test that broke on the
    forty-first declaration would be a test of the calendar.

    What it protects is the ability of the rule to be false. If a
    refactor made `declared_by` stop reaching the bundle, every
    declaration would vanish, the test above would go on passing,
    and it would be verifying nothing.
    """

    inventory = projection.contract_inventory

    assert inventory is not None
    assert inventory.declarations_measured
    assert inventory.declaring >= 40
    assert inventory.implementations >= 154


def test_the_projection_declares_the_commit_it_projects(projection):
    """
    OPS-0002 § *The Context Bundle, and handing one over*: a bundle
    declares a commit of this repository, and not `unknown`.

    **What this guards, measured by mutation on 2026-08-28:** making
    the export lose the commit — `git_commit()` falling back to
    `"unknown"`, which it does whenever git cannot answer — turns
    this red. A projection that names no commit cannot be checked by
    anyone, and the export degrades to that silently.

    **What it does not guard, and the limit is stated rather than
    implied:** an uncommitted change under `docs/`. Adding one and
    re-running leaves this green, because the export reads
    `git rev-parse HEAD` and so does this test — two readings of one
    value, a process apart. The content can therefore be ahead of
    the commit the bundle declares, and nothing here sees it.

    That half is covered by procedure rather than by this test:
    OPS-0002 § 1 refuses to start on a dirty tree —
    `test -z "$(git status --porcelain)"` is the first term of the
    chain — so at publication time the working tree and `HEAD`
    agree. Asserting cleanliness here instead would make the suite
    unusable while editing, which is most of the time it is run.

    **Freshness is not an age**, which is why this asserts a commit
    and not a date.
    """

    import subprocess

    head = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()

    assert projection.source_commit == head, (
        f"the projection declares {projection.source_commit!r} and the "
        f"repository is at {head!r}: the export ran against a different "
        f"commit than the one it is being verified at"
    )
