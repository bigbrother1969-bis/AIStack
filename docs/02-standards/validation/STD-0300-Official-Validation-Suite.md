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
  version: 1.3
  owner: Foundation
  created: 2026-07-31
  updated: 2026-08-22

relations:
  references:
    - STD-0200
    - FDN-0003
    - FDN-0007
    - FDN-0008
    - PRINCIPLES-REGISTRY
    - ADR-0009
    - OPS-0001
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

All generated outputs are disposable (ENG-P-003). Only the criteria are governed.

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
platform proposes, the human decides (GOV-P-001).

---

## 8. Non-Functional Requirements

- Verification shall be automatable; a scenario requiring interactive judgement is
  not yet a criterion.
- Verification cost shall stay compatible with per-commit execution.
- Sustainability: VS-4 exists because resource waste is a governed concern, not a
  performance detail.

---

## 9. Acceptance Criteria

Each criterion carries its own state and, when it has one, the date its
verification was executed. A single date at the head of this section would have
to be rewritten at every change and would be wrong the moment one was missed —
which is how the sentence it replaces came to describe `45710f3` while the
criteria below had moved on. Last change: 2026-08-22, criteria 2.5, 2.6 and 4.9.

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
| 2.5 | `aistack.cli.knowledge_integrity` exits 0 on the bundle used | **satisfied** — 2026-08-22 |
| 2.6 | The same report declares `clean: True` | **satisfied** — 2026-08-22 |

Criteria 2.5 and 2.6 make this scenario self-checking: the suite fails while the
heritage it transmits is itself unsound.

Both are executed by `tests/integration/validation/`, which regenerates the
projection and validates it at every run — § 11 asks that of any criterion that
becomes automated, so that a regression is visible per commit. The bundle is
written to a temporary directory: STD-0002 forbids a test from producing an
operational artifact.

**2.5 was recorded `failing` for eight days after its cause had gone.** The
blocking finding cited was `criticality-discrimination` — *no artifact is
declared C3* — noted on 2026-08-14. Artifacts declaring C3 have existed since
2026-07-24. Nothing distinguished that dead note from a live failure, because no
test ran the validator on the real projection; the two that existed built
synthetic bundles. Verified 2026-08-22 at `506230e`, and mutation-tested by
downgrading the fifteen C3 artifacts to C2, which reproduces the 2026-08-14
finding exactly.

**2.6 exists because measuring 2.5 exposed its limit.** The validator exits 0 on
warnings. Removing `owner` from one governed artifact yields `warnings: 1
clean: False` and an exit code of 0 — this scenario would pass while the heritage
it transmits had degraded. The `clean` field already carried that fact and
nothing read it. It is a separate criterion rather than a stricter 2.5 so that
*degraded* and *broken* keep different weights: a missing metadata field does not
carry the gravity of a heritage with no minimal governed context.

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
| 4.9 | No finding is emitted without at least one evidence reference | **satisfied** — 2026-08-22 |

Criterion 4.5 is not a formality. A single label would make the finding an opinion
about severity; four simultaneous qualifications make it derived knowledge, each
traceable to a distinct policy.

#### What 2026-08-22 verified, and what it did not

The runtime qualification chain decided by ADR-0009 ran for the first time on
2026-08-22 against the reference deployment: 62 containers examined, none
unobserved, the signatures of `OPS-0001` applied to each.

**4.9 is satisfied by construction and was exercised.** `RuntimeFinding` refuses
to be constructed with empty evidence, and the refusal is mutation-tested — the
invariant was removed, the test failed, the invariant was restored. The control
run of 2026-08-22 produced one finding carrying eleven log entries, each
identified by an offset counting back from the newest line and by the timestamp
Docker recorded. Verified at `9e27da3`.

**4.1 remains `not verified`, and only half of it is acquired.** The chain
detects *without being pointed at a service*: run with no argument, it examines
every container the host declares, which is what the criterion asks and what the
ancestor could not do — `analyze_container` required a container name. The other
half is untouched: this chain reads logs and measures no resource whatsoever.
The reference incident above is a CPU consumption diagnosed through system-call
observation, and nothing in the heritage observes system calls. Recording the
acquired half here rather than in the state column is deliberate: a criterion is
satisfied by its whole statement or not at all.

**4.7 remains `not verified`, and the gap has a name.** A finding does cite the
policy that produced it — `OPS-0001/S-004` — which is the citation the criterion
asks for. But every signature in `OPS-0001` declares `grounding: unknown`, and
that field names precisely the policy that would make the *remediation* the right
one. "Check the target service, the exposed port, and the Docker network"
presupposes that a dependency between two services is declared somewhere in this
heritage, and none is. The field was added on 2026-08-22 to make that absence
countable under FDN-0003 Article 12; using its existence to declare the criterion
satisfied would turn an instrument of visibility into a way of hiding what it
measures. This criterion moves when a remediation policy is written, not before.

---

**Suite state: 22 criteria — 6 satisfied, 0 failing, 16 not verified.**

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
- PRINCIPLES-REGISTRY — OPS-P-004 *Observe before acting*, ENG-P-005 *Validate every
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
