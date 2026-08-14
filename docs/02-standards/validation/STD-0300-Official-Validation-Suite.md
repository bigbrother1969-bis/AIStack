---
artifact:
  id: STD-0300
  title: Official Validation Suite
  type: System Specification
  status: Proposed
  version: 1.0
  owner: Foundation
  created: 2026-07-31
  updated: 2026-08-14

relations:
  references:
    - STD-0200
    - FDN-0003
    - FDN-0007
    - FDN-0008
    - PRINCIPLES-REGISTRY
---

# STD-0300 — Official Validation Suite

> Structured per STD-0200. That standard scopes itself to *component*
> specifications; this artifact specifies the system as a whole. Confirming that
> extension of scope, the identifier and the location is a governed decision.
>
> Content extracted from `docs/99-meta/NEXT-SESSION-TODO.md` on 2026-08-14, where
> the project's acceptance criteria sat in an unowned working note. Narrative
> objectives have been rewritten as measurable criteria (§9). Nothing else was
> added.

---

## 1. Problem Statement

AIStack claims that infrastructure knowledge can be governed, explained and
transmitted. Nothing in the heritage states how that claim is proven false.

Without objective acceptance criteria, "AIStack works" is an opinion. That
contradicts the project's own position on technical debt:

> Technical debt is not an opinion.
> It is derived knowledge produced from observations, evidence and explicit policies.

The same standard must apply to the platform itself (FDN-0008, Self-Application).

---

## 2. Purpose

Define the scenarios AIStack shall demonstrate, and the measurable conditions
under which each is considered satisfied.

---

## 3. Responsibilities

This specification owns:

- the list of validation scenarios;
- the acceptance criteria of each scenario;
- the recorded verification state of each criterion.

It does not own:

- how any scenario is implemented;
- the roadmap or the order in which scenarios are addressed;
- the classification or criticality model.

---

## 4. Inputs

- A running Docker host (VS-1, VS-4).
- A generated Context Bundle and its `manifest.json` (VS-2).
- A media catalog and a selection policy (VS-3).
- The runtime observations of the reference incident (VS-4).

---

## 5. Outputs

| Output | Nature |
|---|---|
| Knowledge Catalog of the observed infrastructure | generated |
| Boot Report produced by an onboarded agent | generated |
| Selection artifact | generated |
| Technical debt finding with its evidence references | generated |
| This specification | canonical |

All generated outputs are disposable (ENG-003). Only the criteria are governed.

---

## 6. Constraints

- **Reproducibility** — an unchanged input shall produce an identical output.
- **Explainability** — every statement produced shall be traceable to an
  observation or to an explicit policy.
- **Portability** — no criterion shall depend on a specific host, path or account.
- **Non-interference** — verifying a scenario shall not modify the governed
  heritage nor its published projection.

---

## 7. Functional Rules

- A scenario is satisfied only when **every** one of its criteria holds.
- A criterion that has never been executed is recorded as `not verified`, never
  as satisfied (FDN-0003 Article 12).
- A criterion shall be executable by someone who was not present when it was
  written.
- No scenario is satisfied by a human performing the reasoning on AIStack's
  behalf. The platform produces the finding, or the criterion fails.

---

## 8. Non-Functional Requirements

- Verification shall be automatable; a scenario requiring interactive judgement
  is not yet a criterion.
- Verification cost shall stay compatible with per-commit execution.
- Sustainability: VS-4 exists because resource waste is a governed concern, not a
  performance detail.

---

## 9. Acceptance Criteria

State as of 2026-08-14, bundle `519b4e78…`, repository `d999969`.

### VS-1 — Docker Runtime Discovery

*Demonstrate that AIStack can discover, model and document a Docker
infrastructure automatically.*

| # | Criterion | State |
|---|---|---|
| 1.1 | Given a host running N containers, the generated catalog contains exactly N entries | not verified |
| 1.2 | Each entry carries identity, image, state, published ports and mounts | not verified |
| 1.3 | Regenerating from an unchanged host produces an identical catalog | not verified |
| 1.4 | Every statement in the generated explanation references an observation present in the catalog | not verified |

### VS-2 — Context Bundle / Self-Onboarding

*Demonstrate that AIStack can transmit its governed knowledge to another AI
instance.*

| # | Criterion | State |
|---|---|---|
| 2.1 | An agent given only the bundle produces a Boot Report carrying all eight declared sections | **satisfied** — 2026-08-14 |
| 2.2 | The agent states the bundle's `source_commit` and `content_hash` without external input | **satisfied** — 2026-08-14 |
| 2.3 | The agent identifies Gitea as the Acquisition SPOT and the mirrors as non-authoritative | **satisfied** — 2026-08-14 |
| 2.4 | Two agents of different models declare the same uncertainties and the same READY verdict | not verified |
| 2.5 | `aistack.cli.knowledge_integrity` exits 0 on the bundle used | **failing** — 1 blocking finding |

Criterion 2.5 is what makes this scenario self-checking: the suite fails while the
heritage it transmits is itself unsound. It currently fails on
`criticality-discrimination`.

### VS-3 — Music Sync Selection Pipeline

*Demonstrate that the same Runtime architecture orchestrates a business process,
not only infrastructure.*

| # | Criterion | State |
|---|---|---|
| 3.1 | The same catalog and the same policy produce the same selection | not verified |
| 3.2 | Every included and excluded item carries the rule that decided it | not verified |
| 3.3 | After a user modification, regeneration differs only by the modified items | not verified |

### VS-4 — Sustainability & Technical Debt Analysis

*Demonstrate that AIStack derives technical debt from runtime observations.*

Reference incident: the `aistack-selection-ui` service consumed ≈50 % of one CPU
core while idle, because Uvicorn ran with `--reload` in a permanent container.

| # | Criterion | State |
|---|---|---|
| 4.1 | AIStack emits a finding naming the development option responsible | not verified |
| 4.2 | The finding correlates process, container and deployment definition, each with an observation reference | not verified |
| 4.3 | The recommendation cites the policies it derives from, by identifier | not verified |
| 4.4 | Before/after verification measures a CPU reduction ≥ 95 % (observed: 48–58 % → 0.2 %) | not verified |
| 4.5 | No finding is emitted without at least one evidence reference | not verified |

The incident itself was diagnosed and remediated by a human. That does not satisfy
any criterion above: the point is that AIStack reproduces the reasoning.

---

## 10. Out of Scope

- Performance benchmarking of AIStack itself.
- Validation of third-party runtimes.
- The Adaptive Resource Scheduler and the Knowledge Time Machine — roadmap items,
  not acceptance criteria. They remain in `99-meta`.
- Any criterion requiring a human to interpret the result.

---

## 11. Future Evolution

- Scenarios are added when a capability claims to be demonstrable, never before.
- Criteria migrate from `not verified` to `satisfied` only through an executed
  verification, recorded with its date.
- A criterion that becomes automated should be executed by the same loop as the
  integrity report, so that a regression is visible per commit.

---

## 12. Related Knowledge Artifacts

- STD-0200 — Specification Standard
- FDN-0003 — Constitution (Article 5, Explainability; Article 12, Uncertainty)
- FDN-0007 — Governed Engineering Cycle
- FDN-0008 — Self-Application Principle
- PRINCIPLES-REGISTRY — OPS-004 *Observe before acting*, ENG-005 *Validate every
  architectural step independently*

---

## 13. Related Architecture Decisions

- ADR — Evidence-Driven Observation Architecture (`docs/incoming/`, not yet
  integrated into the governed heritage)
- ADR — Context Bundle Engine
- ADR — Context Bundle Transfer

---

## 14. References

None external. Every criterion derives from artifacts of the AIStack Governed
Heritage.
