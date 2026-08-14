---
artifact:
  id: FDN-0010
  title: Project Working Invariants
  type: Foundation Document
  status: Proposed
  version: 0.1
  owner: Foundation
  created: 2026-08-14
  updated: 2026-08-14

relations:
  references:
    - FDN-0005
    - FDN-0007
    - PRINCIPLES-REGISTRY
---

# FDN-0010 — Project Working Invariants

## Provenance

The five blocks below were the only governed content buried inside the 53 KB
conversation transcript that occupied `The-Sustainable-Heritage-Manifesto.md` until
2026-08-14. They are recovered here so that removing the transcript loses nothing.

They were drafted in conversation and described there as *"désormais des invariants du
projet"*. They have never passed a validation gate. Hence `status: Proposed`.

**Open reconciliation.** Several of these rules restate principles already registered
in PRINCIPLES-REGISTRY — *understand before implementing* is close to ENG-001,
*architecture first* to FDN-009, *migrate incrementally* to ARC-008. This artifact
deliberately does not merge them: it preserves the recovered wording so the overlap
is visible and can be resolved as a governed decision, rather than silently choosing
one formulation over another.

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
