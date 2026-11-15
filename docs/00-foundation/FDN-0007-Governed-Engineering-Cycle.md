---
artifact:
  id: FDN-0007
  title: Governed Engineering Cycle
  type: Foundation Document
  semantic_type: Knowledge Artifact
  domain: Foundation
  confidence: Declared
  criticality: C3
  version: 1.1
  status: Published
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-28

relations:
  references:
    - FDN-0003
    - FDN-0004
    - FDN-0005
    - FDN-0006
---

# FDN-0007 — Governed Engineering Cycle

## Purpose

This document defines the Governed Engineering Cycle.

The Governed Engineering Cycle is the conceptual kernel of AIStack.

It defines the universal lifecycle followed by every governed engineering activity.

---

# Foundational Principle

Every engineering activity begins with observation.

Engineering does not start with transformation.

Engineering starts with governed understanding.

---

# Cycle

```text
Observe

↓

Inventory

↓

Classify

↓

Govern

↓

Transform

↓

Validate

↓

Publish

↓

Observe
```

---

# The scopes this cycle governs

**This cycle is the Single Point Of Truth for the AIStack lifecycle.** It calls
itself universal above, and two other lifecycles are written in the heritage.
Neither competes with it: each is this cycle instantiated at a narrower scope,
and nothing said so until 2026-08-28.

| Lifecycle | Where | Scope it declares, in its own words |
|---|---|---|
| Observe → Inventory → Classify → Govern → Transform → Validate → Publish | here | *every governed engineering activity* |
| Exploration → Discussion → Validation → Knowledge Artifact → Git Commit → Governed Heritage | `FDN-0001` § *Working Workflow* | *every **Foundation contribution*** |
| Proposal → Validation → SPOT Update → Git Commit → Context Bundle Regeneration | `README` § *Development Workflow* | *every **significant modification*** |

The two instances share this cycle's spine — a governed decision, then a
validation, then publication — and each drops the steps its scope does not
reach. A Foundation contribution does not inventory an infrastructure; a code
change does not classify governed knowledge.

**Publication is the one step with an applied procedure.** `OPS-0002` § 1 states
the chain that discharges *Publish* for this repository, command by command. It
is the tail of the two instances above and of this cycle, and it is the only one
of the four that is executed rather than described.

*Recorded because the three coexisted with no declared relation from at least
2026-08-13, when an external boot report raised it (W-15) as *three coexisting
workflow definitions; no artifact declares which one is the SPOT*. The scopes
were already declared, each inside its own document; what was missing is the
sentence relating them.*
