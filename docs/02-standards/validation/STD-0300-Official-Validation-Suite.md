---
artifact:
  id: STD-0300
  title: Official Validation Suite
  type: System Specification
  semantic_type: Specification
  domain: Standards
  criticality: C2
  status: Published
  confidence: Reviewed
  version: 1.1
  owner: Foundation
  created: 2026-07-31
  updated: 2026-08-21

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

---

## Provenance

Content originates from `docs/99-meta/NEXT-SESSION-TODO.md`, where the project's
acceptance criteria sat in an unowned working note.

**Version 1.0 (2026-08-14)** extracted the two validation sections and rewrote their
narrative objectives as measurable criteria. That extraction **silently dropped**:

- the *Expected workflow* chain of the energy-waste case;
- the technical evidence of the reference incident, including the system-call
  observations;
- the *Validated capabilities* lists of scenarios 1, 2 and 3;
- the four-way classification required of a sustainability finding;
- several items of the eight-point validation objective, compressed into fewer
  criteria than the original required.

**Version 1.1 (2026-08-14)** restores all of it. Nothing from the source note is now
absent from this artifact, apart from the two roadmap items — *Adaptive Resource
Scheduler* and *Knowledge Time Machine* — which are not acceptance criteria and
remain in `99-meta`.

The v1.0 omission repeated, at small scale, the defect of commit `76bd373`: content
removed during a restructuring without the change saying so. It is recorded here
rather than corrected in silence.

**Gravé — 2026-08-21.** This specification is governed heritage. What is engraved is an
*extraction*, not a reconstitution: the criteria come from a working note that still
exists in the repository, so this artifact can be checked against its source at any
time. That is why it carries less provenance risk than the three Foundation artifacts
engraved the same day. `confidence: Reviewed`.

`criticality` remains undeclared. Engraving fixes the content, not the qualification;
the criticality of this specification is a separate decision and stays `unknown` rather
than being assumed (FDN-0003 Article 12).

---

## 1. Problem Statement

AIStack claims that infrastructure knowledge can be governed, explained and
transmitted. Nothing in the heritage stated how that claim is proven false.

Two questions motivate this suite:

- Can AIStack transmit its governed knowledge to an agent that has never seen the
  repository?
- **How can AIStack detect and eliminate unnecessary resource consumption?**

Without objective acceptance criteria, "AIStack works" is an opinion. That
contradicts the project's own position:

> Technical debt is not an opinion.
> It is derived knowledge produced from observations, evidence and explicit policies.

The same standard must apply to the platform itself (FDN-0008, Self-Application).

---

## 2. Purpose

Define the scenarios AIStack shall demonstrate, and the measurable conditions under
which each is considered satisfied.

These four scenarios constitute the **first official validation suite of AIStack**.

---

## 3. Responsibilities

This specification owns:

- the list of validation scenarios;
- the capabilities each scenario exercises;
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
- **Explainability** — every statement produced shall be traceable to an observation
  or to an explicit policy.
- **Portability** — no criterion shall depend on a specific host, path or account.
- **Non-interference** — verifying a scenario shall not modify the governed heritage
  nor its published projection.

---

## 7. Functional Rules

- A scenario is satisfied only when **every** one of its criteria holds.
- A criterion that has never been executed is recorded as `not verified`, never as
  satisfied (FDN-0003 Article 12).
- A criterion shall be executable by someone who was not present when it was written.
- No scenario is satisfied by a human performing the reasoning on AIStack's behalf.
  The platform produces the finding, or the criterion fails.

### Expected chain of a sustainability finding

A finding produced under VS-4 shall follow this observable sequence. Each step
consumes the output of the previous one; no step may be skipped or inferred.

```text
Runtime Observation
        ↓
Process and Container Correlation
        ↓
Deployment Configuration Analysis
        ↓
Knowledge Policies
        ↓
Technical Debt Evaluation
        ↓
Sustainability Score
        ↓
Explainable Recommendation
        ↓
Human Validation
        ↓
Remediation
        ↓
Before / After Verification
```

Human Validation is a step of the chain, not a formality appended to it: the
platform proposes, the human decides (GOV-001).

---

## 8. Non-Functional Requirements

- Verification shall be automatable; a scenario requiring interactive judgement is
  not yet a criterion.
- Verification cost shall stay compatible with per-commit execution.
- Sustainability: VS-4 exists because resource waste is a governed concern, not a
  performance detail.

---

## 9. Acceptance Criteria

State as of 2026-08-14, repository `45710f3`.

### VS-1 — Docker Runtime Discovery

*Demonstrate that AIStack can automatically discover, model and document a Docker
infrastructure.*

Capabilities exercised: Runtime observation · Knowledge Catalog generation ·
Artifact generation · Infrastructure explanation.

| # | Criterion | State |
|---|---|---|
| 1.1 | Given a host running N containers, the generated catalog contains exactly N entries | not verified |
| 1.2 | Each entry carries identity, image, state, published ports and mounts | not verified |
| 1.3 | Regenerating from an unchanged host produces an identical catalog | not verified |
| 1.4 | Every statement in the generated explanation references an observation present in the catalog | not verified |

### VS-2 — Context Bundle / Self-Onboarding

*Demonstrate that AIStack can transmit its governed knowledge to another AI
instance.*

Capabilities exercised: Context Bundle generation · PROJECT-CONTEXT ·
NEXT-SESSION-TODO · Knowledge transfer · Self-Onboarding.

| # | Criterion | State |
|---|---|---|
| 2.1 | An agent given only the bundle produces a Boot Report carrying all eight declared sections | **satisfied** — 2026-08-14 |
| 2.2 | The agent states the bundle's `source_commit` and `content_hash` without external input | **satisfied** — 2026-08-14 |
| 2.3 | The agent identifies Gitea as the Acquisition SPOT and the mirrors as non-authoritative | **satisfied** — 2026-08-14 |
| 2.4 | Two agents of different models declare the same uncertainties and the same READY verdict | not verified |
| 2.5 | `aistack.cli.knowledge_integrity` exits 0 on the bundle used | **failing** — 1 blocking finding |

Criterion 2.5 makes this scenario self-checking: the suite fails while the heritage
it transmits is itself unsound. It currently fails on `criticality-discrimination`.

### VS-3 — Music Sync Selection Pipeline

*Demonstrate that the same Runtime architecture can orchestrate a business process
rather than infrastructure only.*

Capabilities exercised: Selection Pipeline · Catalog · Artifact generation · User
interaction · Regeneration.

| # | Criterion | State |
|---|---|---|
| 3.1 | The same catalog and the same policy produce the same selection | not verified |
| 3.2 | Every included and excluded item carries the rule that decided it | not verified |
| 3.3 | After a user modification, regeneration differs only by the modified items | not verified |

### VS-4 — Sustainability & Technical Debt Analysis

*Demonstrate that AIStack can derive technical debt and sustainability issues from
runtime observations.*

#### Reference incident

The permanent `aistack-selection-ui` service consumed approximately 50 % of one CPU
core while idle.

Evidence collected:

- no incoming HTTP requests;
- no active browser session;
- continuous filesystem traversal;
- Uvicorn started with `--reload`;
- the complete Git repository mounted into `/app`.

System-call observation showed repeated `newfstatat`, `getdents64`, `openat` and
`fstat` calls.

**Root cause** — the development-only Uvicorn reload mechanism continuously
monitored the mounted repository.

**Remediation** — remove `--reload` from the permanent container command and rebuild
the image.

**Measured result** — before: approximately 48–58 % of one CPU core; after:
approximately 0.2 % while idle.

The incident was diagnosed and remediated by a human. That satisfies no criterion
below: the point is that AIStack reproduces the reasoning.

#### Criteria

| # | Criterion | State |
|---|---|---|
| 4.1 | AIStack detects abnormal idle resource consumption without being pointed at the service | not verified |
| 4.2 | The finding correlates process, container and deployment definition, each with an observation reference | not verified |
| 4.3 | It identifies the development option enabled in a permanent service | not verified |
| 4.4 | Technical evidence is collected and attached to the finding, down to system-call level or equivalent | not verified |
| 4.5 | The issue is classified **simultaneously** as technical debt, deployment misconfiguration, energy inefficiency and sustainability anomaly | not verified |
| 4.6 | The root cause is explained, derived from the collected evidence | not verified |
| 4.7 | A safe remediation is recommended, citing the policies it derives from by identifier | not verified |
| 4.8 | Before/after verification measures a CPU reduction ≥ 95 % (observed: 48–58 % → 0.2 %) | not verified |
| 4.9 | No finding is emitted without at least one evidence reference | not verified |

Criterion 4.5 is not a formality. A single label would make the finding an opinion
about severity; four simultaneous qualifications make it derived knowledge, each
traceable to a distinct policy.

---

**Suite state: 21 criteria — 3 satisfied, 1 failing, 17 not verified.**

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

- ADR-0008 — Evidence-Driven Observation Architecture (admitted into the governed
  heritage on 2026-08-21; it was in `docs/incoming/` when this suite was written)
- ADR-0005 — Context Bundle Engine
- ADR-0007 — Context Bundle Transfer

---

## 14. References

None external. Every criterion derives from artifacts of the AIStack Governed
Heritage.
