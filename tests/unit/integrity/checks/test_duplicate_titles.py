from aistack.integrity.checks.duplicate_titles import (
    DuplicateTitleCheck,
)


def test_unique_titles_yield_nothing(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(source="a.md", title="alpha"),
        make_artifact(source="b.md", title="beta"),
    ])

    assert DuplicateTitleCheck().evaluate(bundle) == []


def test_collision_is_reported(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(source="a/README.md", title="README"),
        make_artifact(source="b/README.md", title="README"),
        make_artifact(source="c.md", title="other"),
    ])

    findings = DuplicateTitleCheck().evaluate(bundle)

    assert len(findings) == 1
    assert findings[0].affected == 2
    assert findings[0].subjects == ("README (2)",)


def test_undeclared_titles_are_not_a_collision(
    make_artifact,
    make_bundle,
):
    """
    Forty-six artifacts declare no title. They all carry
    UNDECLARED, and counting that as a shared title turned this
    check into a second, noisier report of what
    `metadata-completeness` already says.

    The real collision this check was reporting until 2026-08-21
    — eighteen artifacts sharing "README", "architecture" and
    "specification" — was not a collision either: the builder
    was using filenames as titles and discarding the declared
    ones.
    """

    bundle = make_bundle(
        [
            make_artifact(source="a.md", title="unknown"),
            make_artifact(source="b.md", title="unknown"),
            make_artifact(source="c.md", title="unknown"),
        ]
    )

    assert DuplicateTitleCheck().evaluate(bundle) == []
