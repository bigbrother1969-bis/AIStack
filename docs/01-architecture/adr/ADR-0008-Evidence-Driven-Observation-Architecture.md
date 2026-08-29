---
artifact:
  id: ADR-0008
  title: Evidence-Driven Observation Architecture
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.5
  status: Accepted
  owner: Architecture
  created: 2026-07-31
  updated: 2026-08-29

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
| Execution — Capability, `PackageCapability` and nine implementations | not implemented — measured 2026-08-29 |
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

### The Knowledge Dimension is built, and its four commands were broken

Four CLIs implement it — `docker_catalog`, `docker_discover`,
`docker_selection_catalog`, `compose_catalog` — and ADR-0009 applies the chain
end to end.

**This section read *Four CLIs exercise it* until 2026-08-29, and that was false
for forty days.** Measured by running them: each raised `AttributeError` on the
second line of `main()`, at `ctx.providers.get(...)` — an attribute `Kernel`
does not carry — so none reached a provider. Introduced by `f685f97` on
2026-07-20, which moved `providers` under `registries` and touched none of the
four. **GOV-0002/OS-044**, repaired the same day with one test per `main()`.

*The word matters and is the reason this heading changed. **Exercise** is a
claim about execution; **implement** is a claim about code. This section made
the first while only the second had been measured — the four modules were read,
not run — and a heading that says a dimension is live is exactly where that
distinction has to hold.*

*What ADR-0009 applies end to end is a different chain, through
`runtime_diagnose`, which has its own tests and was never affected.*

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

*Narrowed 2026-08-29. Between 2026-07-20 and that day the four CLIs called
`create_kernel()` and then raised on the next line, so the Kernel was composed
in processes that never completed — GOV-0002/OS-044. The sentence stays because
it is about composition and remains true of it; the qualifier is added because
`live` was doing work the measurement did not support. Since the repair the
four run, and five tests drive them to the artifacts they write.*

**`Observation Service` and `Action` exist nowhere.** There is an `Observation`
and an `ObservationContext`, but they are *results* produced by execution
components and recorded in the trace, not a stage of the chain. Both rows were
left unqualified on 2026-08-27 rather than guessed, and **the owner qualified
them `abandoned` on 2026-08-28**: the chain that was built has no such stages,
and nothing in it waits for one. What this decision anticipated stays written in
§ *Decision*, which is what an abandoned row is for — the intention is preserved
and the table stops reporting it as work in progress.

### The nine capabilities could not be instantiated

**Qualified `done` on 2026-08-27, and measured false on 2026-08-29.**

```text
CompressCapability           own methods=[]  CANNOT INSTANTIATE ('process', 'supports')
DecompressCapability         own methods=[]  CANNOT INSTANTIATE ('process', 'supports')
DecryptCapability            own methods=[]  CANNOT INSTANTIATE ('process', 'supports')
DeserializeCapability        own methods=[]  CANNOT INSTANTIATE ('process', 'supports')
EncryptCapability            own methods=[]  CANNOT INSTANTIATE ('process', 'supports')
HashCapability               own methods=[]  CANNOT INSTANTIATE ('process', 'supports')
SerializeCapability          own methods=[]  CANNOT INSTANTIATE ('process', 'supports')
SignCapability               own methods=[]  CANNOT INSTANTIATE ('process', 'supports')
VerifySignatureCapability    own methods=[]  CANNOT INSTANTIATE ('process', 'supports')
```

Each was `class XCapability(PackageCapability): pass`. `PackageCapability` is an
ABC with two `@abstractmethod`s, so **none of the nine could exist**. They were
not uncalled — they were unusable, and `KnowledgePackage` carries one field,
`id`, so a capability that processed one would have had nothing to process.

**Removed 2026-08-29 by the owner under ARC-P-006**, with the contract kept: a
real packaging operation will be written against `PackageCapability`, and what
is refused is declaring it and stopping there. The row is `not implemented`
because that is now what it is.

### `contract-debt` had been reporting them all along

**This section first said that no instrument saw them. That was wrong, and the
removal itself proved it:**

```text
before   contract-debt   13 of 50 declared contracts satisfied by no class
after    contract-debt    4 of 41
```

**Nine of the thirteen orphans were the nine capabilities.** A class carrying
unimplemented abstract methods *is* a declared contract by this heritage's own
definition — `conformance/inventory.py` inventories it as one, and `FDN-0002`
§ *Contract* says so in words. So each empty subclass was inventoried as a
contract, satisfied by nothing, and **published at every single projection for
five weeks.**

**The check was right and the reading was wrong.** `contract-debt` cannot
distinguish *a contract written before its implementation* — which STD-P-002
makes the prescribed order — from *an implementation that implements nothing*.
Both are a declared contract nobody satisfies.

**And the qualification is what closed the reader's eyes.** Ten of the orphans
were qualified `planned` on 2026-08-23 under `GOV-0002/OS-001`, and the check's
own message says *STD-P-002 makes this an order, not a fault*. **Nine broken
classes were sitting inside a figure that had been declared acceptable** —
qualified debt is still read every day, and read as debt.

*That is the sharpest thing measured on 2026-08-29, and it is not about an
instrument being blind. A qualification is a decision to stop looking at a
number, and it was the right decision for the number. The nine were not in the
number's subject.*

**What the other two instruments did say, measured 2026-08-29:**

- **`false-declarations` reports a class naming a base it does not satisfy.**
  The base **is** satisfied structurally — an empty subclass inherits `supports`
  and `process` with the right call shapes — so it saw nothing, correctly;
- **the test asserted `issubclass`.** `test_package_capabilities_implement_contract`
  checked the declaration and named itself after the implementation. **That is
  the identical mistake recorded on 2026-08-27 for `SshBundleTransfer`**, where
  a test asserted `issubclass` while the claim was `satisfies` — second
  occurrence, in a test written to prove the opposite.

`tests/unit/kernel/test_no_class_declares_a_contract_and_implements_nothing.py`
is the guard: a class whose abstract methods are all inherited and none of which
it declares is an empty declaration. Mutation 2026-08-29 — restoring one of the
nine turns it red; every legitimate abstract base declares its own methods and
is untouched.

*Two neighbours measured the same day and **not** removed, because removing them
is a different decision: `PackageManager` — `kernel/engines/package_manager.py`
— returns its argument unchanged from both methods and its docstring says it
*orchestrates package capabilities*, which are the nine; and its only test
asserts `isinstance(manager, PackageManager)`. It is one of the engines
`ADR-0004`'s § *Implementation state* reads as `done`. Named here, not acted on.*

*And the whole sub-dimension is the shape `GOV-0002/OS-042` recorded for the
Catalog View: **the nine names — serialize, compress, hash — describe exactly
what the Context Bundle export already does by hand**, beside the dimension
built for it. Recorded, not qualified.*

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

**Adapters**: **no class** carries the name, measured 2026-08-28 and confirmed
2026-08-29 across the whole repository — a package does, and the paragraph below
names it. This sentence read *nothing carries the name* until the term was
defined in the Glossary on 2026-08-29, which is when the package was found: a
claim about class names, written in words that covered the repository. The
Providers play the role behind `KnowledgeProvider`, which is interchangeable
exactly as described. The same shape as ADR-0007's `BundleTransferManager` — the
substance under another name — and it was left unqualified on 2026-08-27 for the
same reason: calling it *superseded* would have closed a question nobody had
looked at.

**Both were qualified `superseded` on 2026-08-28, by the owner, in the same
pass**, and the pair is the argument: two decisions naming a component **no
class carries**, whose responsibilities are held by a contract under another
name, in the same heritage and by the same kind of decomposition. A decision
that got its substance is not unfinished.

*That sentence read "a component that exists nowhere" until 2026-08-29. For
`BundleTransferManager` it is still exact; for the Adapter it was not, and the
difference is a package. Corrected rather than left, because the pair is used
here as an argument and an argument built on one imprecise half is worth less
than the qualification it supports.*

**What still asserts the Adapter, named per GOV-0002 § *What a closure must
carry*, rule 2.** `ARCH-0013 — Knowledge Package Architecture` (C2, in the
projection) declares the Adapter **a layer of the architecture** —
*Axioms → Concepts → Engines → Adapters* — with a section stating that Adapters
implement capabilities and remain replaceable. `aistack/transaction/adapters/`
implements the concept at package level. `FDN-0002` defines the term since
2026-08-29.

**None of that reopens this row**, and the distinction is the point: what is
`superseded` here is *this decision's mechanism for technical access*, which
`KnowledgeProvider` carries. The concept is live and governed elsewhere. *This
paragraph was written on 2026-08-29, the day after the qualification: the closure was
taken without it, and rule 2 exists because a closure that names nothing reads
as the retirement of everything the term touches.*

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
