---
artifact:
  id: ADR-0008
  title: Evidence-Driven Observation Architecture
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.2
  status: Accepted
  owner: Architecture
  created: 2026-07-31
  updated: 2026-08-28

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
| Execution — Observation Service | abandoned — 2026-08-28 |
| Execution — Capability, `PackageCapability` and nine implementations | done — 2026-08-27 |
| Execution — Action | abandoned — 2026-08-28 |
| Discovery produces Evidence, never Knowledge | done — 2026-08-27 |
| Qualification is independent from acquisition | done — 2026-08-27 |
| Location abstracts where reality is observed | done — 2026-08-28 |
| Technical access through interchangeable Adapters | superseded — 2026-08-28 |

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
components and recorded in the trace, not a stage of the chain. Both rows were
left unqualified on 2026-08-27 rather than guessed, and **the owner qualified
them `abandoned` on 2026-08-28**: the chain that was built has no such stages,
and nothing in it waits for one. What this decision anticipated stays written in
§ *Decision*, which is what an abandoned row is for — the intention is preserved
and the table stops reporting it as work in progress.

### Two of the five key decisions

**Location** exists — `aistack/location/`, `LocationResolver`,
`FilesystemLocationResolver` — and is consumed by
`transport/filesystem/filesystem_writer.py` **and**
`transport/filesystem/filesystem_receiver.py`. **No observation path uses it.**

*This paragraph said "its only consumer is `filesystem_writer.py`" until
2026-08-28. There are two, both in the same package, and the second was missed
because the first was found first. The measurement was re-run when the row was
qualified, which is why it was caught.*

**Qualified `done` by the owner on 2026-08-28.** The abstraction this row names
exists and is consumed, and the contract holds. That no observation path uses
it is a missing consumer — the condition GOV-0002/OS-039 and OS-041 record for
other components — and not a step of this decision left undone.

**Adapters**: nothing carries the name, measured 2026-08-28 across the whole
repository. The Providers play the role behind `KnowledgeProvider`, which is
interchangeable exactly as described. The same shape as ADR-0007's
`BundleTransferManager` — the substance under another name — and it was left
unqualified on 2026-08-27 for the same reason: calling it *superseded* would
have closed a question nobody had looked at.

**Both were qualified `superseded` on 2026-08-28, by the owner, in the same
pass**, and the pair is the argument: two decisions naming a component that
exists nowhere, whose responsibilities are carried by a contract under another
name, in the same heritage and by the same kind of decomposition. A decision
that got its substance is not unfinished.

*The reading declined is on the record: an Adapter is narrower than a Provider —
one accesses, the other collects and concludes on what it accessed — and nothing
separates the two in the code. Under that reading the row would be `not
implemented`. It was declined because this decision names the Adapter for
**interchangeable technical access**, and that is what `KnowledgeProvider`
delivers.*

*Four unqualified rows is a large number for one decision, and it was the honest
one. FDN-0003 Article 12 makes the absence of a decision a governed state that
must remain visible — and visible is what it was: the four were reported at
every projection for a day and qualified on 2026-08-28, two `abandoned`, one
`done`, one `superseded`. **None of the four went to `not implemented`**, which
is the reading the first measurement suggested for all of them.*
