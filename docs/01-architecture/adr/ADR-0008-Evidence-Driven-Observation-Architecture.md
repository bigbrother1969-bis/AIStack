---
artifact:
  id: ADR-0008
  title: Evidence-Driven Observation Architecture
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.1
  status: Accepted
  owner: Architecture
  created: 2026-07-31
  updated: 2026-08-27

relations:
  references:
    - STD-0300
---

# ADR-0008 — Evidence-Driven Observation Architecture

This file supersedes the previous draft and freezes the architectural decision.

## Status

Accepted.

Admitted into the governed heritage on 2026-08-21, from `docs/incoming/`, where it
had been sitting since 2026-07-31.

## Decision
AIStack separates the **Execution Dimension** from the **Knowledge Acquisition Dimension**.

Execution:
```
Request -> Task -> Kernel Runtime -> Observation Service -> Capability -> Action
```

Knowledge:
```
Reality -> Evidence -> Evidence Normalization -> Canonical Observations -> Item Qualification -> Knowledge Assets -> Governed Heritage
```

Key decisions:
- Discovery produces Evidence, never Knowledge.
- Qualification is independent from acquisition.
- Location abstracts where reality is observed.
- Technical access is implemented through interchangeable Adapters.
- Migration remains incremental.

## Implementation state

Measured 2026-08-27. **This decision cuts the architecture in two, and the two
halves are not in the same state.**

| Step | State |
|---|---|
| Knowledge — Reality → Evidence, providers collect and conclude nothing | done — 2026-08-27 |
| Knowledge — Evidence Normalization, `normalize_log_evidence` | done — 2026-08-27 |
| Knowledge — Canonical Observations, `RuntimeObservation` and `LogEntry` | done — 2026-08-27 |
| Knowledge — Item Qualification, `qualify` against the declared catalogue | done — 2026-08-27 |
| Knowledge — Knowledge Assets → Governed Heritage, `KnowledgeArtifact` and the Context Bundle | done — 2026-08-27 |
| Execution — `Request` | done — 2026-08-27 |
| Execution — `Task`, `TaskRegistry`, `TaskResolver` | done — 2026-08-27 |
| Execution — Kernel Runtime, `KernelRuntime` / `RuntimeExecutor` / `ExecutionTrace` | done — 2026-08-27 |
| Execution — Observation Service | unqualified — 2026-08-27 |
| Execution — Capability, `PackageCapability` and nine implementations | done — 2026-08-27 |
| Execution — Action | unqualified — 2026-08-27 |
| Discovery produces Evidence, never Knowledge | done — 2026-08-27 |
| Qualification is independent from acquisition | done — 2026-08-27 |
| Location abstracts where reality is observed | unqualified — 2026-08-27 |
| Technical access through interchangeable Adapters | unqualified — 2026-08-27 |

*The fifth key decision — *migration remains incremental* — is **not in the
table**. It is a policy this decision adopts about how the rest arrives, not a
step that can reach a terminal state, and a row for it would be reported as
unfinished at every projection for ever. It was written as a row and removed
the same hour, for that reason.*

**One table, on purpose.** It was written as three — Knowledge, Execution, key
decisions — and `unfinished-decisions` read only the first, because it stops at
the first table of the section. **That stopping rule is not a defect**:
ADR-0009 carries a second table inside its own implementation section whose
cells are commands, and a parser collecting every row would report a command as
an unfinished step forever. So the decision is shaped to be read, rather than
the reader loosened.

*Found on 2026-08-27 by the count staying at 2 when four rows had just been
left open — and the prose here had already claimed all four were reported. A
sentence asserting a protection that was not delivered, in the artifact written
to end that pattern, within the hour.*

### The Knowledge Dimension is live

Four CLIs exercise it — `docker_catalog`, `docker_discover`,
`docker_selection_catalog`, `compose_catalog` — and ADR-0009 applies the chain
end to end.

### The Execution Dimension is built and nothing runs it

Measured 2026-08-27:

```text
KernelRuntime.boot()   → called by tests only; no CLI boots the Runtime
nine capabilities      → no caller outside their own package and the tests
tasks registered       → 0
```

**The last line is the one that matters.** `create_kernel()` registers catalog
views, providers and selection strategies, and registers **no task**, so
`TaskResolver` resolves against an empty registry. The dimension is not merely
uncalled: it has nothing to execute. GOV-0002/OS-041.

`create_kernel()` itself is live — the four CLIs use it. What has no production
caller is the **Runtime layer above the Kernel**, which is narrower than *the
kernel is unused* and is what the measurement supports.

**`Observation Service` and `Action` exist nowhere.** There is an `Observation`
and an `ObservationContext`, but they are *results* produced by execution
components and recorded in the trace, not a stage of the chain. Both rows are
left unqualified rather than guessed.

### Two of the five key decisions

**Location** exists — `aistack/location/`, `LocationResolver`,
`FilesystemLocationResolver` — and its only consumer is
`transport/filesystem/filesystem_writer.py`. **No observation path uses it.**
The abstraction is built; the use this decision names it for is not there.

**Adapters**: nothing carries the name. The Providers play the role behind
`KnowledgeProvider`, which is interchangeable exactly as described. The same
shape as ADR-0007's `BundleTransferManager` — the substance under another name
— and left unqualified for the same reason: calling it *superseded* would close
a question nobody has looked at.

*Four unqualified rows is a large number for one decision, and it is the honest
one. FDN-0003 Article 12 makes the absence of a decision a governed state that
must remain visible.*
