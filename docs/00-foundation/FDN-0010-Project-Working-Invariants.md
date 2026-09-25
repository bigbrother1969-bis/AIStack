---
artifact:
  id: FDN-0010
  title: Project Working Invariants
  type: Foundation Document
  semantic_type: Knowledge Artifact
  domain: Foundation
  criticality: C3
  status: Published
  confidence: Reviewed
  version: 1.1
  owner: Foundation
  created: 2026-08-14
  updated: 2026-09-25

relations:
  references:
    - FDN-0005
    - FDN-0007
    - FDN-0012
---

# FDN-0010 — Project Working Invariants

## Provenance

The five blocks below were the only governed content buried inside the 53 KB
conversation transcript that occupied `The-Sustainable-Heritage-Manifesto.md` until
2026-08-14. They are recovered here so that removing the transcript loses nothing.

They were drafted in conversation and described there as *"désormais des invariants du
projet"*. They had never passed a validation gate, and this artifact stood at
`status: Proposed` until the engraving recorded below.

**Open reconciliation.** Several of these rules restate principles already registered
in FDN-0012 — *understand before implementing* is close to ENG-P-001,
*architecture first* to FDN-P-009, *migrate incrementally* to ARC-P-008. This artifact
deliberately does not merge them: it preserves the recovered wording so the overlap
is visible and can be resolved as a governed decision, rather than silently choosing
one formulation over another.

**Gravé — 2026-08-21.** This artifact is governed heritage and its version moves from
0.1 to 1.0. What is engraved is a *reconstitution*: an AI assistant selected these five
blocks out of a 53 KB conversation transcript, and that selection — what counted as an
invariant and what did not — is now invariant itself. The owner has accepted it.
`confidence: Reviewed`.

The open reconciliation stated above is **not** closed by this engraving. Several of
these rules still restate principles registered in FDN-0012. Engraving fixes
the wording as heritage; it does not decide the overlap.

**Resolved 2026-09-25 by the owner, `GOV-0002/OS-062`.** Both levels are kept,
deliberately, the same shape `OS-003` decided for `ARC-P-005` and `FDN-P-015`.
`FDN-0012` states each principle as governed, citable, C-tier content: the
table a check counts. This artifact states a subset of them as a working rule
for daily practice — *understand before implementing*, *architecture first*,
*migrate incrementally* read as instructions, not as identity statements —
alongside content `FDN-0012` does not carry at all: the anti-goals, the
Decision Rule chain, the Sprint Success Criterion. Neither is a copy of the
other, and no line below was reworded by this closure. No principle changes
identifier or table entry, unlike `OS-003`: every one of them was already
registered before this decision, so nothing here is newly countable. This
paragraph is kept rather than deleted, per `GOV-0002` § *What a closure must
carry*: it is what first named the gap, dated 2026-08-21, 35 days before it
closed.

---

## 1. Working Rules

Always:

- understand before implementing;
- preserve working heritage;
- migrate incrementally;
- avoid big-bang rewrites;
- validate every architectural concept on a real use case;
- architecture first;
- documentation before implementation.

---

## 2. Anti-goals

Do not:

- build generic frameworks;
- introduce concepts without a validating use case;
- rewrite functioning code because a cleaner architecture exists;
- optimize prematurely;
- replace governed knowledge by AI reasoning.

---

## 3. Decision Rule

Whenever several architectural options exist:

```text
Real use case
        ↓
Simplest architecture
        ↓
Explicit contracts
        ↓
Incremental migration
        ↓
Validation
```

---

## 4. Sprint Success Criterion

> The sprint is complete only when a real AIStack capability has been improved and
> validated on the Gigabyte infrastructure.

An architecture that is merely elegant does not close a sprint.

---

## 5. Maturity Snapshot

Recorded as of the transcript, 2026-07. **Not maintained here** — a maturity state is
an observation, not an invariant, and it belongs to `PROJECT-CONTEXT` or to a
generated report. It is preserved only so the recovery is complete.

| Area | State |
|---|---|
| Foundation | Stable |
| Architecture | Stable enough for implementation |
| Governance | Operational |
| Runtime | Incremental alignment in progress |
| Knowledge Providers | First production implementation |
