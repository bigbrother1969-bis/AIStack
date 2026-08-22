---
artifact:
  id: ADR-0009
  title: Runtime Evidence Qualification
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Proposed
  owner: Architecture
  created: 2026-08-22
  updated: 2026-08-22

relations:
  references:
    - ADR-0008
    - STD-0300
    - STD-0102
    - FDN-0011
---

# ADR-0009 — Runtime Evidence Qualification

## Status

Proposed.

The decisions below were taken by the owner on 2026-08-22. This record is
written the same day and submitted for acceptance the next, per the working
rule adopted on 2026-08-21: an act that binds the heritage is proposed one
day and accepted the following one.

## Context

A container named `aistack-backend` has been running on this deployment
since before the governed repository existed. Its image was built on
2026-07-01; the repository's first commit is 2026-07-04.

Its source is 361 lines of FastAPI and static JavaScript, held in
`/srv/aistack`, a second git repository that contains this one as a
subdirectory and was declared nowhere until 2026-08-21. Nine navigation
modules are announced, one is implemented; the application itself renders
*"Module prévu, pas encore implémenté"* for the other eight.

**The owner qualified it on 2026-08-22 as an initial experimenter**, whose
purpose was to establish that knowledge can be recovered from an existing
Docker implementation. That qualification is what this ADR acts on: an
experiment that has produced its result is not maintained, it is harvested.

What it established is concentrated in about twenty lines of
`analyze_container`: four log signatures learned from operating this
homelab, each with an interpretation and a remediation.

```python
if "AUTH_FAILED" in logs:                     → OpenVPN credentials
if "Your credentials might be wrong" in logs: → NordVPN / Gluetun credentials
if "TLS Error" in logs:                       → VPN server, certificates, network
if "connection refused" in logs.lower():      → target service, port, Docker network
```

Verified on 2026-08-22: none of these four strings appears anywhere in the
governed heritage — not in the 290 lines of Docker code spread over eleven
files, not in any document. The observation side exists and is better; the
interpretation side does not exist at all.

STD-0300 § VS-4 specifies that interpretation — *Runtime Observation → … →
Explainable Recommendation* — and its nine acceptance criteria are all
recorded as `not verified`. The experimenter is a crude, partial, working
answer to a specification written three days after it.

## Decision

The experimenter's function migrates into AIStack. Its code does not.

### 1. The chain is ADR-0008's chain

Nothing new is invented where ADR-0008 already decided:

| ADR-0008 stage | This migration |
|---|---|
| Reality | the running containers |
| Evidence | `docker logs` output, collected and not interpreted |
| Evidence Normalization | a builder that turns raw output into a typed model |
| Canonical Observation | the model the qualifier consumes |
| Item Qualification | matching against the declared signature catalogue |

`ARC-P-012` cuts the chain at Evidence: the provider collects logs and
concludes nothing. The experimenter does both in one function, which is why
its code does not migrate.

`ARC-P-013` forbids the rest of it: *evaluation consumes canonical knowledge
models, never raw technical output*. `if "AUTH_FAILED" in logs` is substring
matching on an undifferentiated blob. The normalization stage exists to make
each log entry an identified thing a finding can reference.

### 2. Qualification consumes governed knowledge — the inversion

ADR-0008's chain ends in the Governed Heritage: reality becomes knowledge.

This one runs the other way at its last stage. The signature catalogue is
governed knowledge, and the qualifier **reads** it. Evidence is qualified
*against* the heritage rather than *into* it, and the result is an
operational report — disposable under `ENG-P-003`, never a Knowledge Asset.

This is the first time `docs/` becomes an input to execution. Until now the
heritage was written by humans, projected as opaque content, and parsed by
nothing. A document that code reads acquires a machine contract in addition
to its human one, and that contract has to be explicit — which is what
FDN-0011 calls the difference between a contract and a claim.

### 3. Signatures are declared, not coded

The four signatures are the owner's operational knowledge, learned from
incidents on this deployment. `GOV-P-001` forbids the AI from authoring
them, extending them, or rewording them.

They live in a governed artifact under `docs/`, with an owner, a criticality,
a version, and for each signature: its pattern, its interpretation, its
remediation, and the identifier of the policy the remediation derives from —
`STD-0300` § VS-4 criterion 4.7 requires that citation.

Coding them into a Python module would reproduce, on the day it was
described, the defect this heritage spent 2026-08-20 and 2026-08-21
removing: knowledge embedded in code rather than declared.

### 4. One parser, two call sites

The catalogue is written as a delimited structured block inside the document
body. Prose stays free everywhere else; the one place where an edit can
break execution is visible as a block.

That block is parsed **at projection**, by a blocking integrity check. A
malformed catalogue stops a publication, exactly as the eight existing
checks do. The same parser is reused at runtime, on the document, so there
is one contract and not two, and diagnosing a container does not require a
regenerated bundle.

The alternative — the qualifier consuming only the published bundle — is a
stricter reading of `ARC-P-013` and was rejected on use: it would make
`export_project_sources.py` a precondition of every diagnostic.

### 5. Identifiers

The catalogue takes a new prefix, `OPS-`, and STD-0102's prefix table gains
it. `KnowledgeDomain` gains `Operations`.

The heritage has carried Operations principles since July — `OPS-P-001` to
`OPS-P-004` — while the code's domain vocabulary had six values and not that
one. An artifact declaring `domain: Operations` would have been normalized to
`unknown`. The domain was missing from the implementation, not from the
knowledge.

### 6. Scope: iso-usage on capability, not on defects

Everything the experimenter lets a person do today remains doable. Its
measured usage is three interactions: list containers with a state icon,
request a global diagnostic, analyse one container's logs. Two of its routes
— `/{name}/logs` and `/api/ollama/models` — have no caller in its own
interface and are not usage.

Two behaviours are corrected rather than reproduced:

- the state icon computes `health.get("Status", "healthy")`, so **a container
  with no healthcheck is displayed as healthy**. Most containers on this
  deployment declare none. Article 12 of FDN-0003 requires three states:
  healthy, unhealthy, undeclared;
- the global diagnostic renders `JSON.stringify(data, null, 2)` in a `<pre>`.
  The capability is kept; that rendering is not a view.

One behaviour is added, because VS-4 criterion 4.1 asks for detection
*without being pointed at a service*: the qualifier evaluates every
container, where the experimenter requires a container name.

The web surface follows the pattern the repository already established.
`selection_ui/` is 331 lines, lives at the repository root outside `src/`,
imports the governed library, and ships as its own digest-pinned image. The
new surface is built the same way. It is not part of `src/aistack`.

## Consequences

Positive:

- four signatures stop being a side effect of one function and become
  governed, owned, versioned knowledge;
- `STD-0300` § VS-4 criteria 4.6, 4.7 and 4.9 become structurally reachable:
  evidence reference and cited policy are fields of the finding, not
  intentions;
- the experimenter can be retired, and what it established survives it.

Negative:

- `docs/` enters the execution chain. A governed document now has readers
  that are not human, and editing one can break a diagnostic;
- a new prefix and a new domain value widen two closed vocabularies;
- `IntegrityFinding` cannot be reused. Its contract states *"It proposes no
  remediation"*, and VS-4 requires one. A second finding type is introduced —
  not for symmetry, but because the two differ in what they are about and in
  whether they recommend.

## Implementation state

Nothing is implemented. This ADR records a decision, not a state.

The contracts come first (`ARC-P-005`), then the catalogue declared by its
owner, then collection, normalization, qualification, a CLI, and last the
web surface.

## Related Artifacts

- `ADR-0008` — Evidence-Driven Observation Architecture, whose chain this
  applies and whose last stage this inverts
- `STD-0300` — Official Validation Suite, § VS-4
- `STD-0102` — Naming Conventions, which this revises
- `FDN-0011` — Contract-Based Engineering
