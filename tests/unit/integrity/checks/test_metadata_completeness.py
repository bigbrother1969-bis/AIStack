from aistack.integrity.checks.metadata_completeness import (
    MetadataCompletenessCheck,
)


COMPLETE = """---
artifact:
  id: FDN-0009
  title: AI Collaboration Protocol
  type: Foundation Protocol
  version: 1.0
  status: Proposed
  owner: Foundation
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


def test_complete_declaration_yields_nothing(make_artifact, make_bundle):

    bundle = make_bundle([make_artifact(content=COMPLETE)])

    assert MetadataCompletenessCheck().evaluate(bundle) == []


def test_absent_declaration_is_reported(make_artifact, make_bundle):

    bundle = make_bundle([make_artifact(content="# No frontmatter\n")])

    findings = MetadataCompletenessCheck().evaluate(bundle)

    assert len(findings) == 1
    assert "no metadata block" in findings[0].summary
    assert findings[0].affected == 1


def test_partial_declaration_is_reported(make_artifact, make_bundle):

    bundle = make_bundle([make_artifact(content=PARTIAL)])

    findings = MetadataCompletenessCheck().evaluate(bundle)

    assert len(findings) == 1
    assert "incomplete" in findings[0].summary
