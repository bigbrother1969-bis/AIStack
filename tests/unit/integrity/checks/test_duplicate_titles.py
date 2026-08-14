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
