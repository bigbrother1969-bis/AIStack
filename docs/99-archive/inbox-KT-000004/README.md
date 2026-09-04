# KT-000004 — archived, not integrated

**Archived 2026-09-03**, `GOV-0002/OS-049`.

These two packages sat in `inbox/knowledge/`, untriaged, from 2026-07-18
(their own file dates) until this entry closed them. A third file in the
same directory, `ADR-000X-Python-Packaging-v1.md`, was deleted rather than
archived: it was verified to be a strict subset of the numbered
`ADR-0001-Python-Packaging-v1.md` — every section it carries, `ADR-0001`
already carries, plus everything added to that ADR since.

**Why archived rather than integrated.** Both packages target document
paths that do not exist in this repository (`docs/00-foundation/engineering-principles.md`,
`docs/04-development/knowledge-transport-layer/LESSONS-LEARNED.md`,
`docs/04-development/git-transaction-engine/LESSONS-LEARNED.md`,
`docs/07-roadmap/ROADMAP.md`) and use an unnumbered, free-form artifact
shape that predates the `FDN-XXXX` / `ADR-XXXX` / `ARCH-XXXX` numbered
convention this heritage settled into. The concept they describe under
*Knowledge Transport Layer* / *Knowledge Artifact Router* is not absent
from the governed heritage — `FDN-0002` (the Glossary) already names a
`TransportOperationEngine` filling that role — it simply took a different
shape than either package proposed, and integrating either literally would
mean inventing document types nothing else in this repository uses.

**Not discarded.** `FOUNDATION-Finish-the-Capability.md` (in
`KT-000004-Knowledge-Transaction.zip`) and its near-duplicate in
`KT-000004-lessons-for-transport-layer.zip` state a real engineering
principle — implementation before tooling, once a capability is under
way — verified 2026-09-03 to have no governed home. It is named here as a
candidate for a future foundation artifact, deliberately, rather than
acted on as a side effect of closing this residual.
