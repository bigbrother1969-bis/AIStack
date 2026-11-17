from aistack.integrity.checks.metadata_completeness import (
    REQUIRED_FIELDS,
    MetadataCompletenessCheck,
)


COMPLETE = """---
artifact:
  id: FDN-0009
  title: AI Collaboration Protocol
  type: Foundation Protocol
  semantic_type: Policy
  domain: Foundation
  criticality: C3
  version: 1.0
  status: Published
  confidence: Reviewed
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-21
---

# Body
"""

PARTIAL = """---
artifact:
  id: FDN-0009
  title: AI Collaboration Protocol
---

# Body
"""

LIFECYCLE_BLOCK = """---
artifact:
  id: FDN-0009
  title: AI Collaboration Protocol
  type: Foundation Protocol
  semantic_type: Policy
  domain: Foundation
  criticality: C3
  version: 1.0
  status: Published
  confidence: Reviewed
  owner: Foundation

lifecycle:
  created: 2026-07-06
  updated: 2026-08-21
---

# Body
"""


def test_the_twelve_fields_of_std_0100_are_required():

    assert set(REQUIRED_FIELDS) == {
        "id",
        "title",
        "type",
        "semantic_type",
        "domain",
        "criticality",
        "version",
        "status",
        "confidence",
        "owner",
        "created",
        "updated",
    }


def test_complete_declaration_yields_nothing(make_artifact, make_bundle):

    bundle = make_bundle([make_artifact(content=COMPLETE)])

    assert MetadataCompletenessCheck().evaluate(bundle) == []


def test_absent_declaration_is_reported(make_artifact, make_bundle):

    bundle = make_bundle([make_artifact(content="# No frontmatter\n")])

    findings = MetadataCompletenessCheck().evaluate(bundle)

    assert len(findings) == 1
    assert "no metadata block" in findings[0].summary
    assert findings[0].affected == 1


def test_each_missing_field_is_named(make_artifact, make_bundle):
    """
    "incomplete metadata block, 38/84" tells an owner nothing
    they can act on. Naming the field does.
    """

    bundle = make_bundle([make_artifact(content=PARTIAL)])

    findings = MetadataCompletenessCheck().evaluate(bundle)

    summaries = " | ".join(f.summary for f in findings)

    assert "but do not write version" in summaries
    assert "but do not write owner" in summaries
    assert "but do not write criticality" in summaries

    # what the artifact *did* declare is not reported missing
    assert "but do not write id" not in summaries
    assert "but do not write title" not in summaries


def test_dates_in_a_separate_block_do_not_count(
    make_artifact,
    make_bundle,
):
    """
    STD-0100 v2.0 defines a single `artifact:` mapping. Dates
    declared in a sibling `lifecycle:` block are not where the
    standard says to look, so a consumer reading the governed
    structure will not find them — and the check must say so
    rather than accept a second convention.

    14 artifacts of the heritage were in this state on
    2026-08-21.
    """

    bundle = make_bundle([make_artifact(content=LIFECYCLE_BLOCK)])

    findings = MetadataCompletenessCheck().evaluate(bundle)

    summaries = [f.summary for f in findings]

    assert any("but do not write created" in s for s in summaries)
    assert any("but do not write updated" in s for s in summaries)
    assert len(findings) == 2
