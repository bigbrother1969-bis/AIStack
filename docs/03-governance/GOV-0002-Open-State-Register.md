---
artifact:
  id: GOV-0002
  title: Open State Register
  type: Governance Register
  semantic_type: Knowledge Artifact
  domain: Governance
  criticality: C2
  confidence: Declared
  version: 1.21
  status: Draft
  owner: Foundation
  created: 2026-08-22
  updated: 2026-08-23

relations:
  references:
    - FDN-0011
    - GOV-0001
    - STD-0100
---

# GOV-0002 — Open State Register

## Purpose

This register records what AIStack knows about itself and has not resolved.

Until 2026-08-22 that knowledge lived in AI session records under `claude/`,
which is to say in notes with no owner, outside the projection, and readable
only by whoever thought to open them. The heritage has already paid for that
once: STD-0300 was extracted from an unowned working note on 2026-08-14,
because acceptance criteria were sitting in a file nobody governed.

An open state is not a failure. It is a fact about the system that has been
observed, stated, and not yet closed. What this register forbids is the
third possibility — observed, and quietly forgotten.

## What belongs here

An entry states one condition of the system that is known and unresolved.
Six natures are used today:

| Nature | What it is |
|---|---|
| `contract-debt` | A defect of the contract architecture, per FDN-0011 |
| `non-conforming` | An instance that violates a rule the heritage declares |
| `defect` | Code that does not do what it is meant to do |
| `published` | An artifact already published that must be rebuilt |
| `risk` | An exposure that is understood and not closed |
| `decision` | A question that requires the owner and has not been answered |

## What does not belong here

A wish, a roadmap item, or an improvement nobody has observed the need for.
`docs/99-meta/roadmap/` holds those, outside the projection, and they are not
open states — they are intentions.

## The relationship to FDN-0011

FDN-0011 defines technical debt as a property of the contracts, and states
that it is *derived from violations of the contract architecture rather than
from subjective code reviews*.

That ambition is respected here rather than contradicted, and the distinction
matters: **`contract-debt` is the only nature in this register that is
derivable**. As of 2026-08-22 the others are declared, because nothing
derives them.

An entry carries a `derivable` field for that reason. When a nature becomes
derivable, its entries stop being maintained by hand and become the output of
a check, and the register measures its own automatability.

**One nature crossed that line on 2026-08-22.** `contract-debt` is now
derived: `aistack.conformance.inventory` walks the package at every
projection, the archive carries the result, and the `contract-debt` integrity
check publishes it. OS-001 no longer holds a figure an agent asserted — it
holds one the validator republishes, identically, on every supported
interpreter.

What that does **not** change is qualification. The check states how many
contracts nothing satisfies; STD-P-002 makes a contract ahead of its
implementation the prescribed order, so which of them are planned and which
abandoned stays with the owner under GOV-P-001. A derivable nature is one
whose *facts* are measured, not one whose *judgements* are automated.

This register is not a second view of the code. It is the primary record of
conditions no artifact states about itself.

## Resolution is recorded, never removed

A resolved entry stays, with the date and what discharged it.

The reason is a defect found on 2026-08-22 in STD-0100. Its version 2.0 had
carried, since 2026-08-20, the sentence *"the validator shall also observe
`version`, `created` and `updated`, **which it does not today**"*. The work
was done on 2026-08-21 by `085fe3b`. The sentence was never updated, and a
C2 standard spent a day asserting something about the code that had stopped
being true.

The defect was not the deferral — a deferral honoured within a day is the
method working. The defect was that **nothing distinguished a live deferral
from a discharged one**. Deleting resolved entries here would rebuild that
same blindness.

## Qualification is dated and attributed

An entry's `Qualification` field carries either `unknown` or a decision, and a
decision carries the date it was taken and who took it. GOV-P-001 puts that
act with the owner: the register may measure a condition, and may lay out the
readings, but it may not choose between them.

**Ten entries were qualified on 2026-08-23**, in one pass — every entry then
open. What each was decided *against* is kept in place, because a decision
whose alternatives have been erased reads as the only thing anyone thought of.

A qualified entry is not a resolved one. Six of the ten still carry work, and
stay in their section until it is done.

## How an entry is written

```
#### GOV-0002/OS-000 — one-line statement

**Nature** · **Opened** · **State** open | resolved YYYY-MM-DD by <what>
**Observed** where and how it was measured, so a reader can re-measure it
**Derivable** yes | no | yes, once <what> exists
**Qualification** what the owner must decide, or `unknown`
```

Entry identifiers are fragments of this register's identifier, as signatures
are of their catalogue (ADR-0009 § 3.2). An entry is not a governed object
citable from anywhere; it exists inside the register that declares it.

---

# Contract debt

#### GOV-0002/OS-001 — Twenty declared contracts are satisfied by nothing

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** open

**Where the current figure lives.** Since `4010d1f` the count is published
by the `contract-debt` integrity check at every projection, and carried in
the archive as `contract-inventory.json`. **This entry deliberately does not
repeat it.** A number copied here would be stale at the next commit — it
already was, within one — and the point of OS-002 was to stop the debt being
a figure someone wrote down.

```
python3 -m aistack.cli.knowledge_integrity
```

What stays here is what the check cannot say. **The count became a count on
2026-08-23**: `aistack.funnel` was removed (OS-018) and every module of the
package now imports, so the inventory is complete and no longer publishes an
upper-bound caveat. Should a module stop importing, the caveat returns as its
own observation and a test names the module.

**First measured** 2026-08-22 at `9099df7`: 56 contracts, 20 orphans,
identical on Python 3.11, 3.12 and 3.13. That last clause is the entry's own
history — the first published figure was 20 on one machine and 22 on
another, because the tool mistook a CPython 3.12 internal for a contract
requirement. OS-019 records what let it through.

**The earlier figure of seventeen was wrong**, and it is left here rather
than overwritten. It came from a throwaway script that no longer exists,
run before OS-008 was closed, so it walked past 33 files including the
integrity validator — and it ran an instrument with two defects, one of
which under-declared the debt by reading `__annotations__` instead of the
attributes a contract declares.

Ten of the orphans are one family:
`PackageCapability` and its nine specialisations — `Compress`, `Decompress`,
`Encrypt`, `Decrypt`, `Hash`, `Serialize`, `Deserialize`, `Sign`,
`VerifySignature` — declared together and implemented never. `TransferTarget`
is another: transfer code exists, and implements `BundleTransfer` instead.

*Three earlier measurements of this were wrong and are recorded in the
session log: nominal inheritance (meaningless for structural Protocols), a
structural pass that reported `IntegrityCheck` as orphan while seven checks
implement it, and a claim that `pyproject.toml` omitted ten directories from
the distribution — disproved by building the wheel and reading its contents.*

The other ten as of `4010d1f`, listed so that qualifying them does not
require a re-run: `KnowledgeEngine`, `KnowledgeGenerator`, `KnowledgePolicy`,
`KnowledgeRenderer`, `EvidenceCollector`, `DiscoveryProvider`,
`KnowledgePipeline`, `KnowledgeProvider`, and `kernel.execution.task.Task` —
plus `TransferTarget` named above. The check's `subjects` field carries the
live list; this one is a snapshot for reading, not the reference.

**Derivable** yes — and it now is, at every projection. OS-002 was what
stood in the way.
**Qualification** **decided 2026-08-23 by the owner, for ten of the twenty.**
The `PackageCapability` family — the contract and its nine specialisations —
is **planned, not abandoned**. STD-P-002 makes a contract ahead of its
implementation the prescribed order, and this is that order. It stays in the
package, and its ten orphans become qualified debt rather than unqualified.

The other ten remain `unknown`, and this is the half no tool will ever close:
`KnowledgeEngine`, `KnowledgeGenerator`, `KnowledgePolicy`,
`KnowledgeRenderer`, `EvidenceCollector`, `DiscoveryProvider`,
`KnowledgePipeline`, `KnowledgeProvider`, `kernel.execution.task.Task` and
`TransferTarget`. The entry stays open for them, and the figure the check
publishes does not change: twenty orphans, ten of them now answered for.

#### GOV-0002/OS-025 — The declared environment names an interpreter it does not provide

**Nature** `contract-debt` · **Opened** 2026-08-23 · **State** open
**Observed** On 2026-08-23 the owner ran the governed command,
`source bin/aistack_env.sh && pytest -q`, on a shell where the virtual
environment was not active. `python3` was the system 3.12. The file printed
both of its warning lines and the suite ran anyway: 514 passed, and
`test_the_suite_runs_on_the_interpreter_the_heritage_declares` failed — the
test written the day before, catching the owner of the heritage that declares
it.

ADR-0001 designates `bin/aistack_env.sh` as the **single source of truth for
the execution environment**, and ENG-TEST-0002 is C3 and promises
*reproducibility, deterministic execution, portability across environments*.
Since 2026-08-23 that file names the interpreter — `3.13` — and it provides
nothing. Both machines carry a `uv`-created virtual environment holding a
conforming interpreter, and **no artifact of this heritage names it, says
where it lives, or says that it must be active**.

So the governed command is not the whole command. What actually has to be
typed is `source .venv/bin/activate` first, and that instruction exists in one
person's shell history — the condition FDN-P-004 exists to end, and the same
shape as the interpreter itself before OS-019.

The warning is deliberate and stays: this file is sourced, so a `return` on a
mismatch would drop the developer out of the setup they asked for. What is
undeclared is not the warning, it is the environment the warning is about.
**Derivable** partly, and already half-derived. That `python3` is not the
declared version is detected twice over — by the file's own warning and by the
test. That the machine holds a conforming interpreter elsewhere, and where, is
not derivable from anything written.
**Qualification** `unknown`. Three readings, and the third is what is in
force today without being declared:

- **the SPOT provides the environment.** `bin/aistack_env.sh` activates a
  virtual environment at a declared path, and creates it if absent. The file
  designated as the source of truth for the environment would then be the
  environment. It also means a sourced file that mutates the caller's shell
  well beyond exporting variables.
- **the launchers refuse.** The declaration stays a declaration and the three
  `bin/` entry points exit on a non-conforming interpreter. Enforcement moves
  to the things that run, and the warning stays a warning for someone who
  sources the file by hand.
- **the environment is deployment configuration**, like the transfer route in
  `config/context_bundle_transfer.yml`: not governed, not versioned, the
  developer's responsibility, and the existing warning is the whole treatment.
  This is what happens today. Choosing it would mean writing it down, so that
  the next person to run the governed command on a bare shell learns it from
  an artifact rather than from a red test.

#### GOV-0002/OS-003 — `ARC-P-005` and FDN-0011's second principle state one rule twice

**Nature** `contract-debt` · **Opened** 2026-08-21 · **State** open
**Observed** `ARC-P-005` reads *contracts before implementations*. FDN-0011's
second principle, *Contract First Engineering*, says the primary deliverable
of engineering is a governed set of contracts. The same rule at two
altitudes. Recorded in FDN-0012 v2.1 rather than resolved, and the
second was deliberately not registered.
**Derivable** no
**Qualification** **decided 2026-08-23 by the owner.** **Both levels are
kept, deliberately.** `ARC-P-005` states the architectural rule; FDN-0011's
second principle states the founding one. They are not a duplicated
formulation but one rule at two altitudes, and collapsing them would lose the
altitude.

The consequence is that the second stops being unregistered: it enters
FDN-0012 as `FDN-P-015`, so that a reader does not take it for a principle
someone forgot, and so that `principle-identifiers` counts it like the
others.

#### GOV-0002/OS-017 — A sentence about the code can become false and nothing sees it

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** open
**Observed** Six occurrences, in three C2 artifacts. Four were found on
2026-08-22; two more on 2026-08-23, both inside the two documents that state
the rule — STD-0100 and this register. The count is dated because it will
grow.

STD-0100 v2.0 carried *"the validator shall also observe `version`, `created` and
`updated`, **which it does not today**"* from 2026-08-20 until 2026-08-21, one day
after `085fe3b` had done the work. That one is already the reason this register
never deletes a resolved entry.

The other three are in STD-0300, and were found by reading it rather than by any
check:

- criterion 2.5 recorded **failing** since 2026-08-14 on *no artifact is declared
  C3*, a cause that had gone on 2026-07-24 — three weeks before the note was
  written. Eight days of a validation suite declaring itself in failure.
- the acceptance section headed *State as of 2026-08-14, repository `45710f3`*
  while the criteria under it had moved.
- the engraving block asserting that `criticality` *remains undeclared* while the
  front-matter of the same file declared `C2`, both dated 2026-08-21.

The fifth and sixth were produced by closing OS-004. STD-0100 said the
`type` → `domain` rule *"is stated and not yet enforced"* and this register said it
*"is enforced by nothing"*; the check written on 2026-08-23 made both false, and
neither would have been noticed by anything but a reader following the citations.

All six share one shape: a true statement about a moving system, written without
the date that made it true. Nothing distinguishes such a sentence from a live one,
and the cost is asymmetric — a stale *"it does not do X"* makes a heritage look
worse than it is, and a stale *"it does X"* makes it look better.

**Derivable** partly. The temporal markers that hide a date — *today*,
*currently*, *still*, *not yet*, *remains*, *for now* — are detectable by pattern.
Whether the sentence carrying one is stale is not.
**Qualification** **decided 2026-08-23 by the owner.** **The pattern check is
written, and it publishes `OBSERVATION`.**

The markers that hide a date — *today*, *currently*, *still*, *not yet*,
*remains*, *for now* — are listed at every projection. Whether a sentence
carrying one has gone stale stays a reading, so the check states where to look
and never says `clean: False`. A `WARNING` would fail on the historical
quotations this heritage keeps on purpose, which is the trap
`principle-identifiers` avoided the same day by refusing to read prose for the
retired three-digit form.

Six occurrences in two days is the argument. A false positive costs a reading
here; a stale sentence costs a decision taken on it.

*This paragraph read "like the `type` → `domain` rule of OS-004, it is enforced by
nothing" until 2026-08-23, when OS-004 was closed. A fifth occurrence of the shape
this entry exists to record, inside the entry itself, found while closing the rule
it named.*

---

# Non-conforming instances

#### GOV-0002/OS-023 — `<ID>-<Title>.md` does not describe this heritage

**Nature** `non-conforming` · **Opened** 2026-08-23 · **State** open
**Observed** STD-0102 mandates `<ID>-<Title>.md`. Measured 2026-08-23 across
the 65 artifacts of the projection: **25 do not follow it**. OS-006 and
OS-007 were recorded as two isolated instances; they were the two that
happened to be noticed.

The 25 are not 25 mistakes. They are families, and at least three of them
look deliberate:

- **components.** `CMP-0001` through `CMP-0012` each hold `README.md`,
  `architecture.md` and `specification.md` inside their own directory. That
  is a coherent convention — and it produces four files named
  `architecture.md`, so a filename no longer identifies an artifact.
- **section READMEs.** `FDN-0001-README.md`, `STD-0001-README.md`, and the
  repository's own `README.md`, whose declared title is *AIStack Main
  README*.
- **the Manifesto**, `The-Sustainable-Heritage-Manifesto.md`, declaring
  `id: FDN-MANIFESTO` — a name chosen to be read, on a document that opens
  the heritage.

The rest are near-misses where the title is longer than the filename:
`ADR-0005-Context-Bundle-Engine.md` declares *Context Bundle Engine
Architecture*, and three others like it.

*This entry exists because the agent wrote into OS-007 that a
`filename-conformance` check now enforced the rule — before writing it, and
before measuring. Measuring first is what turned a one-line check into a
governance question.*
**Derivable** yes — comparing `source` against `id` and `title` is one pass
over the bundle, and it is written the moment the rule is settled
**Qualification** **decided 2026-08-23 by the owner.** **The rule is
retired.** `<ID>-<Title>.md` stops being governed. Since OS-021 the projection
is keyed on `id`, so a filename carries no identity and the constraint had
become decorative. STD-0102 is amended, no `filename-conformance` check is
written, and no file is renamed.

OS-006 and OS-007 stay resolved, and were not mistakes. A file whose name
contradicted its declared title was worth fixing while the name was what a
reader had. What is retired is the rule that turned those two into a
permanent obligation over 25 artifacts following other conventions on
purpose.

---

# Defects

None open. OS-009 and OS-010, the two defects of `sync_mirrors.sh`,
were resolved on 2026-08-23 and are in *Resolved*.

An empty section is kept rather than removed: a register with no defects
section could not be told from one that never looked for any.

---

# Published artifacts

None open. The only entry of this nature, OS-011, is in *Resolved*.

An empty section is kept rather than removed, for the same reason as
*Defects*: it states that this heritage publishes artifacts and currently
has none in a doubtful state, which is not the same as a register that never
thought to look.

---

# Risks

#### GOV-0002/OS-012 — `aistack-backend` exposes an unauthenticated API holding a writable Docker socket

**Nature** `risk` · **Opened** 2026-08-21 · **State** partially mitigated
**Observed** `GET /api/docker/containers` answers 200 with no credentials,
and `[ -w /var/run/docker.sock ]` is true inside the container — which is
root on the host. Until 2026-08-21 it also sat on the `proxy` network with 43
containers including WordPress. Mitigated the same day: bound to
`127.0.0.1:8010`, removed from `proxy`, verified unreachable by name from
another container. **The API itself is unchanged.**
**Derivable** no
**Qualification** **decided 2026-08-23 by the owner.** Neither authenticate
nor accept: **retire the component.** ADR-0009 already decides the migration
of `aistack-backend`'s function, and authenticating something scheduled for
removal is work thrown away.

The remainder of ADR-0009 therefore becomes the priority, and this entry
closes when the surface disappears rather than when it is defended. It stays
open until then; the mitigation of 2026-08-21 holds meanwhile — bound to
`127.0.0.1:8010`, off the `proxy` network.

---

# Decisions

#### GOV-0002/OS-022 — Parallel experimentation is a practice nothing declares

**Nature** `decision` · **Opened** 2026-08-23 · **State** open
**Observed** The owner runs proof-of-concept work outside this repository and
integrates it when it is ready. Two instances exist, and both produced a
governed decision **after** the fact rather than under a rule:

- the **ancestor**, `/srv/aistack`, qualified by ADR-0009 on 2026-08-22 as
  *an initial experimenter*, whose four log signatures became `OPS-0001`;
- **QUAL-0001**, in `/srv/aistack/ollama/governed-llm/`, a 64-test campaign
  qualifying local LLMs against four levels of governed context. Technically
  complete, `Human evaluation pending`, and cited by no artifact here.

The practice is deliberate and it works. What is undeclared is the practice
itself: nothing in the heritage says that an experimentation space exists
outside the projection, how a POC enters it, what makes one integrable, or
who decides. `docs/99-meta/roadmap/` holds intentions and is explicitly not
this.

The cost is visible in how both cases were handled. Each required an
architecture decision written from scratch, and the second one — a campaign
that measures a founding principle, since QUAL-0001/P005 shows a model
asserting that AI is the source of truth, which GOV-P-001 forbids — is
currently reachable only by someone who knows the directory exists.

*An earlier version of this entry read that knowledge "keeps being born
outside the repository", as if by accident. The owner corrected it: the
experiments are parallel by design. The defect is not the practice, it is
that the practice is undeclared.*
**Derivable** no
**Qualification** **decided 2026-08-23 by the owner.** **A section in
FDN-0005, not an ADR.** The Project Operating Model states that an
experimentation space exists outside the projection, and how a POC enters it.

Two observed cases justify declaring that the practice exists. They do not
justify deciding its states, its criteria and its authority in advance, which
is what an ADR would have had to do.

What the section has to make possible, and nothing more: that QUAL-0001 be
citable by the heritage while its human evaluation is still pending.

#### GOV-0002/OS-013 — The ancestor's relation to the heritage is undecided

**Nature** `decision` · **Opened** 2026-08-21 · **State** open
**Observed** `/srv/aistack` is a git repository that contains the governed
one as a subdirectory. It holds the source of `aistack-backend:0.10`, built
2026-07-01, three days before this repository's first commit. Backed up
2026-08-22 to a private Gitea repository, `aistack-origin`. ADR-0009 decides
the migration of its function; it decides nothing about the repository
itself.
**Derivable** no
**Qualification** **decided 2026-08-23 by the owner.** **This repository is
the product; `/srv/aistack` is an archive.**

Both readings were defensible and led to opposite architectures. The one
chosen means that whatever still lives in the ancestor migrates here or ends
there, and that `aistack-origin` is a permanent backup rather than a second
line of development.

#### GOV-0002/OS-014 — An installed AIStack cannot read the governed catalogue

**Nature** `decision` · **Opened** 2026-08-22 · **State** open
**Observed** ADR-0009 § 2 makes `docs/` an input to execution: `OPS-0001`
declares the signatures, and `runtime_diagnose` resolves them from the
repository root. The wheel contains `aistack/` and nothing else — verified
2026-08-22 by building it and reading its contents, the same measurement that
disproved the packaging hypothesis recorded in OS-001. An installed AIStack
therefore fails with an explicit message and must be given `--catalogue`.

The failure is loud rather than silent, which is why this is a decision and
not a defect. What is undecided is whether a knowledge policy the product
executes belongs inside the distribution.
**Derivable** yes — a check that every path the code resolves under `docs/`
exists in the built distribution
**Qualification** **decided 2026-08-23 by the owner.** **An installed
AIStack is a different subject from a governed one**, and a governed one
requires the repository.

`docs/` is not shipped in the wheel: that would make governed knowledge an
artifact of distribution, versioned by the wheel rather than by its SPOT, and
would put two copies of it in the world — which FDN-P-005 forbids.
`--catalogue` stays optional and the failure stays loud.

This entry recorded the third reading as the most inconvenient of the three.
It was chosen for the reason it was inconvenient.

#### GOV-0002/OS-015 — Nothing declares which containers are expected to run

**Nature** `decision` · **Opened** 2026-08-22 · **State** open
**Observed** First real run of `runtime_diagnose`, 2026-08-22: 62 containers
swept, one finding — eleven connection refusals in `frigate`, exact in
detection and empty in remediation. `frigate` is stopped on purpose on this
deployment; it is started on demand for Oak-15 and shut down after. Those
lines are what an nginx prints while its backend goes away.

`Signature.applies_to` was added the same day and treats the symptom: a rule
can now say it means something only on a running container. It does not close
the gap. The heritage cannot tell *stopped because broken* from *stopped on
purpose*, because no artifact states which containers this deployment expects
to be running. That knowledge exists in one person's head, which is the
condition FDN-P-004 exists to end.
**Derivable** no — there is nothing to derive it from, and that is the entry
**Qualification** **decided 2026-08-23 by the owner.** **The expected state
of a deployment is not declared here.** This repository describes a product;
the set of containers one host expects to be running describes that host, and
declaring it here would make every other installation contradict it.

`Signature.applies_to` remains the only treatment, and remains deliberately a
treatment of the symptom. The gap it leaves is real, and is now outside this
repository's scope rather than pending inside it.

---

# Resolved

An entry moves here with the date and what discharged it, and is never
deleted. A register that erased what it had closed could not show that a
rule ever bound anything.

#### GOV-0002/OS-005 — The `<DOMAIN>-P-NNN` convention is enforced by nothing

**Nature** `contract-debt` · **Opened** 2026-08-21 · **State** resolved 2026-08-23 by `principle-identifiers`
**Observed** STD-0102 v2.0 renumbered every principle to `<DOMAIN>-P-NNN`.
Writing `FDN-006` in FDN-0012 tomorrow would pass every check.
The renumbering itself missed the Operations family — four principles and one
citation — and that gap survived a day undetected.
**Resolved 2026-08-23.** Measured first: 49 principles across six domains,
102 citations of them, all resolving. The `principle-identifiers` check reads
the rows of FDN-0012 positionally rather than by pattern — a reader that
collected cells *matching* the form would have found only conforming ones and
reported `FDN-006` as absent rather than as wrong, which is the failure this
entry describes.

Two facts are published, because they are two questions: a registered
identifier that does not carry the form, and a cited identifier no row
declares. The second is what the missed Operations family would have been.

**They do not carry the same severity, and the second was corrected on the
day it was written.** A malformed row is a `WARNING` — no state of the work
has a principle registered under a name the standard forbids. A citation the
registry does not declare is an `OBSERVATION`, and it was a `WARNING` for
four hours: it fired on the commit that qualified this entry's own family,
where the register recorded a decision to create `FDN-P-015` and `ENG-P-007`
before the rows existed. `clean: False` forbade recording a decision before
its consequence, which is this heritage's method.

That is the asymmetry `reference-integrity` was given `OBSERVATION` for the
same day. The occurrence this entry was opened for is still published at
every projection, which is what would have caught it a day earlier.

**What the check deliberately does not do** is read prose for the old
three-digit form. Fourteen occurrences remain in the heritage and every one is
a quotation — FDN-0012 and STD-0102 both recount the renumbering and cannot do
so without naming what they retired. A check over prose cannot tell a
quotation from a live citation, and would report a heritage that documents its
history as one that failed to migrate. That boundary is stated in STD-0102
v2.2 rather than left to whoever next reads the check.

The closed set of domain prefixes had no existence before this: it was
whatever people had happened to write. It is now in
`src/aistack/contracts/classification.py` beside the domain vocabulary.
`Knowledge Assets` is absent from it, deliberately — no principle has been
registered in that domain, so no prefix has been decided, and deciding one is
the owner's under GOV-P-001.
**Derivable** yes — a check over the registry's identifiers
**Qualification** none required; the convention is decided.

#### GOV-0002/OS-004 — `type` → `domain` is stated and enforced by nothing

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** resolved 2026-08-23 by `classification-coherence`
**Observed** STD-0100 v2.1 states that a declared `type` determines its
`domain`. Measured across 63 artifacts and 16 distinct types with no
exception. No integrity check verifies it; it holds because it has been
applied by hand.
**Resolved 2026-08-23.** Re-measured first, as OS-023 had just shown why:
65 artifacts, 19 distinct types, still no exception. The
`classification-coherence` check derives the rule at every projection and
`test_no_declared_type_maps_to_two_domains` runs it over this repository's
own heritage at every suite. Severity `WARNING`, not `OBSERVATION` — unlike
a dangling reference, which can legitimately precede the document it cites,
no state of the work has one type belonging to two domains.

The check is deliberately one axis wide. STD-0100 names two artifacts that
depend on that — `FDN-0011` and `ARCH-0009` — and two tests hold the
boundary, so a later reader who completes the rule to `semantic_type` and
`criticality` learns it from a red suite rather than from two broken
artifacts.
**Derivable** yes — a check comparing declared types across the bundle
**Qualification** none required; the rule is decided.

#### GOV-0002/OS-024 — A principle sits in FDN-0012 with no identifier and no row

**Nature** `non-conforming` · **Opened** 2026-08-23 · **State** resolved 2026-08-23 by registering it as `ENG-P-007`
**Observed** Found while writing the `principle-identifiers` check, by reading
what the registry contains rather than what its tables declare.

Between the Engineering table and the Operations heading, FDN-0012 carries
*Contracts Derive from Policies* — four screens declaring `Domain: Engineering`,
`Criticality: C2 — Governed Principle`, the word **Principle**, a full statement,
an engineering chain and its architectural consequences. It has no identifier and
no row in any table.

So it is a governed principle by every property it declares about itself, and it
is invisible to everything that reads the registry: the 49 the check counts do
not include it, nothing can cite it, and `FDN-P-014` — *technical debt is a
property of the contracts* — sits in a table three screens above while its
fuller statement sits outside one.

It also carries the truncated sentence beginning *"Different"*, introduced
already incomplete by `685bcc8` on 2026-08-01 and recorded as lost under
FDN-0003 Article 12. Whatever is decided about the principle, that note travels
with it.

**Derivable** partly. That a heading declaring `Criticality:` and `Principle`
carries no identifier is detectable. Whether a block of prose *is* a principle is
not, and this one was found by reading.
**Qualification** **decided 2026-08-23 by the owner.** **It becomes
`ENG-P-007`, with a row.** It is what the block already declares itself to be;
registering it only makes that legible to everything that reads the registry.
It becomes citable, the count goes from 49 to 50, and `principle-identifiers`
verifies it like the others.

The truncated sentence beginning *"Different"* travels with it, still recorded
as lost under FDN-0003 Article 12 rather than quietly dropped by the
registration.

**Resolved 2026-08-23.** It is `ENG-P-007 — Contracts derive from Policies`,
with a row in the Engineering table and a heading that carries the identifier.
The count goes from 49 to 50, the two forward citations this register carried
are gone, and `principle-identifiers` verifies it like the others.

Its content is unchanged, and the truncated sentence beginning *"Different"*
travels with it — still recorded as lost under FDN-0003 Article 12 rather than
dropped by the act of numbering.

#### GOV-0002/OS-007 — `ADR-0003-Selection-Engine.md` does not carry its full title

**Nature** `non-conforming` · **Opened** 2026-08-21 · **State** resolved 2026-08-23 by the rename
**Observed** Its declared title is *Selection Engine Strategy Delegation*.
The same check as OS-006 would find it.
**Resolved 2026-08-23.** The file is
`ADR-0003-Selection-Engine-Strategy-Delegation.md`. Nothing cited the old
name — verified before renaming — so unlike OS-006 this touched no
identifier and no reference.
**Derivable** yes, and deliberately not derived yet — see OS-023. Writing
that check was the plan; measuring first showed it would accuse 25 of the 65
artifacts, so the rule has to be settled before it can be enforced.
**Qualification** none required; a rename of the file, not of the identifier.

#### GOV-0002/OS-009 — `sync_mirrors.sh` stops at the first failing mirror

**Nature** `defect` · **Opened** 2026-08-21 · **State** resolved 2026-08-23 by publishing every mirror independently
**Observed** On 2026-08-21 GitHub rate-limited the SPOT host and `set -e`
ended the run. Codeberg was reachable and was never published. One mirror is
not a dependency of another.
**Resolved 2026-08-23.** The mirrors are a list, each attempted whatever the
others did, and every failure is named at the end. The run still fails — a
partial synchronization must not look complete to whatever reads the exit
code — but it fails *after* having done everything it could do.

Writing the fix produced a second defect that was not in the entry. Calling
`publish` inside an `if` suspends `set -e` for everything it calls, so a
failed `git push` no longer ended the function: it fell through to the lines
that count commits and announced a publication that had not happened. Every
failure now returns rather than raises, and a test watches for the
announcement.

`tests/integration/scripts/test_sync_mirrors.py` builds a SPOT, a clone and
two mirrors as real repositories under `tmp_path`, and breaks one by pointing
its URL at nothing — which is what a rate-limited host looks like from the
laptop. Three of its ten tests fail against the version this replaces; the
other seven are controls, and the entry says so rather than claiming ten.
**Derivable** no
**Qualification** none required.

#### GOV-0002/OS-010 — `sync_mirrors.sh` pulls its own new version mid-run

**Nature** `defect` · **Opened** 2026-08-21 · **State** resolved 2026-08-23 by parsing the whole file before running any of it
**Observed** The run that delivered the script's own improvement printed the
old message: bash had already read the old file. Harmless at this size; on a
larger file the shell can resume at a shifted byte offset.
**Resolved 2026-08-23.** Everything the script does now lives inside `main`,
invoked on the last line as `main "$@"; exit $?` — both commands on one line,
so that even if `main` ever returned instead of exiting, the `exit` is
already parsed and bash reads no further byte of a file the pull may have
replaced.

**The dangerous case is not reproducible at this size**, and the test says so
instead of pretending to observe it: bash reads a file this small in one
chunk. What is observed is that a pull which rewrites the script does not
change the running process, and that the structural guard is present — a
guard nothing watches is removed by the next person who finds it odd.
**Derivable** no
**Qualification** none required.

#### GOV-0002/OS-016 — An evidence extract can omit the pattern that fired the rule

**Nature** `defect` · **Opened** 2026-08-22 · **State** resolved 2026-08-23 by centring the extract on the match
**Observed** First complete run of `runtime_diagnose` on 62 containers,
2026-08-22, with `S-004` temporarily widened to `any` as a control case. The
`frigate` evidence lines carry three timestamps — Docker's, the container's
own, and nginx's — and the report's 90-character extract reached
`connect() failed (1` and stopped. `connection refused`, the pattern that
fired `OPS-0001/S-004`, sat outside the extract. The finding carried all
eleven lines in full; the report showed everything about them except what
they proved.

Mitigated the same day: the width is 200, which covers every line this
deployment produced, and a cut extract now says how many characters it hides
— the rule the line count already followed.
**Resolved 2026-08-23.** The extract is centred on the match, so the width
now bounds how much context is shown and no longer decides whether the
pattern is visible. `MatchedLine` carries the line and the position, and the
position lives there rather than on `LogEntry` because it is a property of
the encounter between a rule and a line, not of the line — `ARC-P-012` keeps
the provider on the far side of that boundary.

Two defects surfaced while making the change, both recorded in the commit:
`tuple[MatchedLine, ...]` accepted bare `LogEntry` objects, because an
annotation is not a check; and a test asserting `pytest.raises(Exception)`
began passing because the constructor refused its fixture, so the assignment
it existed to test was never reached.

One case remains open by design, and it is declared rather than hidden: a
case-insensitive comparison whose folding changes the text length yields no
usable index — `ß` folds to `ss` — so `match_at` is `None` and the extract
falls back to the start of the line. Centring on an index computed against a
string no container printed would be worse than not centring at all.
**Derivable** no
**Qualification** none required; the decision was taken 2026-08-23.

#### GOV-0002/OS-019 — The suite runs on one interpreter and three are supported

**Nature** `non-conforming` · **Opened** 2026-08-22 · **State** resolved 2026-08-23 by narrowing the range and checking it
**Observed** `pyproject.toml` declares `requires-python = ">=3.11"`, so
3.11, 3.12 and 3.13 are all supported. Nothing runs the suite on more than
one: whichever the machine happens to have. The published images are
`python:3.13-slim`; the owner's laptop is 3.13.5; the agent's container is
3.11.

Concretely, on 2026-08-22 the contract inventory reported 20 orphans on
3.11 and 22 on 3.12 and 3.13, at the same commit (`2904336`). It was found
because two people ran it on two machines, not because anything checked.
Fixed at `9099df7`, and the mutation test that guards the fix is *killed on
3.13 and survives on 3.11* — the machinery it removes does not exist there.
The suite therefore proves strictly less on the interpreter it ran on than
on the one the images ship.

ENG-TEST-0002 is C3 and promises *reproducibility, deterministic execution,
portability across environments*. It declares the source roots and says
nothing about the interpreter, so the declared execution environment
declares an incomplete environment — the same shape of gap the principle's
own v2.0 was written to close.
**Resolved 2026-08-23.** The owner narrowed the range:
`requires-python = ">=3.13"`, which is what the published images and the
SPOT host run. A portability nothing verified is given up rather than
claimed.

**The check caught the agent before the owner did, in the commit that
introduced it.** That commit stated 3.13 was also what the owner's laptop
ran. It was 3.12. The figure had been read off a `python3 -VV` that executed
on the SPOT host — the preceding `cd` had failed there, which said so — and
the agent reported it as the laptop's without ever measuring the laptop.
The suite went red on the one machine that runs it, with the reason in the
assertion message.

Measured 2026-08-23, after the fact and not before: laptop 3.12, SPOT host
3.13.5, images `python:3.13-slim`, agent container 3.11 and 3.13. The owner
aligned the laptop to 3.13 rather than widen the range back, so the
declaration and the deployment now name one version.

Narrowing alone would have moved the defect instead of closing it — the
agent's container runs 3.11, so the suite would have kept passing on an
interpreter outside the declared range, which is worse than before because
the claim would then be explicit. Three things close it together:

- `bin/aistack_env.sh`, designated by ADR-0001 as the SPOT for the execution
  environment, now names the interpreter as well as the source roots, and
  warns when they disagree. A warning and never an exit: the file is
  sourced, and a `return` would drop the developer out of the setup they
  asked for.
- `tests/unit/test_declared_interpreter.py` reads `requires-python` and
  compares it to the running interpreter, so a suite passing on an
  unsupported version says so instead of looking green.
- the agent installed 3.13 in its container and runs the suite there.
  Verified 2026-08-23: 463 tests pass on 3.13, and the interpreter test
  fails on 3.11 with the reason.

A second test asserts the range is exactly `>=3.13`, so widening it again is
deliberate and arrives with the matrix that would make it true.
**Derivable** yes — the check does it at every run
**Qualification** none required; the decision was taken 2026-08-23.

#### GOV-0002/OS-021 — The projection loses the governed identifier

**Nature** `contract-debt` · **Opened** 2026-08-23 · **State** resolved 2026-08-23 by keying artifacts on their identifier
**Observed** `MarkdownArtifactBuilder` sets `id=discovery.content_hash`, so
every artifact in the bundle is keyed by a SHA-256 and **`FDN-0003` appears
nowhere in the model**. It survives only inside the `content` string, as
text in the frontmatter, alongside the prose.

The same hash is also written to `metadata["content_hash"]`, so the value is
carried twice and the field named `id` holds neither an identity the heritage
declares nor a name anyone cites.

Measured 2026-08-23: a check comparing declared references against
`artifact.id` reports 85 dangling references on a heritage that has none.
`reference-integrity` therefore parses the frontmatter to recover what the
model dropped — a check re-deriving from prose what the pipeline had in its
hands.

The consequence for VS-2 is the sharp one. An agent handed the bundle cannot
resolve *"what does FDN-0003 say"* without parsing 65 frontmatter blocks,
and the contract `KnowledgeArtifact` documents every field except this one:
`id: str` carries no comment, where `declared_type`, `domain` and the rest
carry paragraphs.
**Resolved 2026-08-23.** The owner chose the honest naming: `id` carries the
governed identifier and the hash moves to `metadata["content_hash"]`.

Measured before switching: the 65 artifacts declare 65 distinct identifiers,
so keying on them loses nothing.

**The switch would have broken the mirror equivalence, silently.**
`compute_content_hash` read `artifact.id`, which worked only because that
field held the content hash. Fingerprinting the new `id` would have hashed
the *names*: two bundles carrying the same 65 identifiers over different text
would have proven equivalent, and the property the manifest exists for would
have stopped meaning anything without any test failing. It now reads
`metadata["content_hash"]`, and the published fingerprint is byte-identical
before and after — verified on the real projection.

`reference-integrity` no longer parses the frontmatter to recover identity;
it reads the model. And `KnowledgeArtifact.id` now carries a comment, which
it never had — the one field of that contract without one was the one nobody
could interpret.
**Derivable** yes — comparing `artifact.id` against the frontmatter `id` is
one pass over the bundle
**Qualification** none required; the decision was taken 2026-08-23.

#### GOV-0002/OS-020 — A declared reference is checked against nothing

**Nature** `contract-debt` · **Opened** 2026-08-23 · **State** resolved 2026-08-23 by `reference-integrity`
**Observed** Every artifact may declare `relations: references:`. Measured
2026-08-23 across the 64 artifacts carrying a declared `id`: **21 distinct
identifiers are cited, and one designated nothing** —
`PRINCIPLES-REGISTRY`, cited five times while the registry's identifier was
`FDN-PRINCIPLES`. The five were the Manifesto, FDN-0009, FDN-0010, FDN-0011
and STD-0300; four of the five are C3.

They were corrected on 2026-08-23 with the rename of OS-006, so the count is
zero today. **What is not corrected is that nothing measures it.** No
integrity check compares the set of cited identifiers against the set of
declared ones, so the next broken reference will be as invisible as these
five were — and a reference is how the heritage says two artifacts belong
together.

The measurement is one pass over the bundle and needs no new input: both
sets are already in the projection.
**Resolved 2026-08-23** by the `reference-integrity` check, the ninth.
The owner chose `OBSERVATION`: a `WARNING` would make `clean: False` and
fail STD-0300 criterion 2.6 until every reference resolves, which would also
forbid committing an artifact that cites a document being written.

Two facts are published separately rather than summed. A dangling reference
is a statement that is wrong; an unreadable frontmatter is a statement
nobody could read, and reporting them together would let *no broken
references* and *nobody could tell* read identically.

**Writing it exposed OS-021.** A first version compared references against
`KnowledgeArtifact.id` and reported **85 dangling references** on a heritage
that has none — `FDN-0003` among them, cited twelve times. The bundle keys
its artifacts by content hash, so the governed identifier is not in the
model at all, and the check now reads it from the frontmatter.
**Derivable** yes — the check does it at every projection
**Qualification** none required; the decision was taken 2026-08-23.

#### GOV-0002/OS-011 — `aistack-core:0.1.0` carries bytecode the heritage does not know about

**Nature** `published` · **Opened** 2026-08-22 · **State** resolved 2026-08-23 by unpublishing the image
**Observed** Built 2026-08-19 under a `.dockerignore` whose `__pycache__` and
`*.pyc` patterns matched only the context root, so every
`src/aistack/**/__pycache__` entered the image. Corrected in the file on
2026-08-22 by `108b8a7`; the published image predates the correction and is
pinned by digest in `docker-compose.yml`.
**Resolved 2026-08-23.** The owner deleted the image from DockerHub rather
than rebuilding it. Nothing in the repository depended on it: measured
2026-08-23, `docker-compose.yml` declares `image: aistack/core:local` and
builds from the local `Dockerfile`, so the published digest appeared only in
a comment documenting how it had been produced.

Unpublishing rather than rebuilding is the stronger answer to what the entry
described. A rebuilt image would have to be verified before publication and
then stay verified; an image nobody pulls cannot diverge from the heritage
that describes it.
**Derivable** no
**Qualification** none required; the decision was taken 2026-08-23.

#### GOV-0002/OS-018 — `aistack.funnel` has never been able to run

**Nature** `defect` · **Opened** 2026-08-22 · **State** resolved 2026-08-23 by removing the module
**Observed** `src/aistack/funnel/` holds one file, `__main__.py`, 82 lines of
argparse CLI whose first import is `from .core import FunnelError,
decapsulate, encapsulate, inspect`. There is no `core.py`, and there never
was: `2c8018f`, 2026-07-17, added `__main__.py` alone. This is not a deleted
module, it is a module that was never committed.

`python3 -m aistack.funnel version` raises `ModuleNotFoundError` before
parsing a single argument. Verified 2026-08-22. The four names it imports
appear nowhere else in the repository, and nothing anywhere references
`funnel` — no test, no script, no document, no entry point.

Five weeks undetected, and the reason is OS-008: without `__init__.py`,
`pkgutil` never descended into the directory, so every discovery pass walked
straight past it. The defect and the blind spot that hid it were the same
directory. It surfaced within seconds of closing OS-008 — the first thing the
newly-visible tree said.

It ships. The built wheel contains it.
**Searched before deciding, 2026-08-23.** Every branch, every commit and
every dangling commit of this repository: `funnel/` has only ever held
`__main__.py`. On the deployment host, `git log --all -- "*funnel*"` in the
ancestor repository returns nothing and no `funnel/core.py` exists anywhere
under `/srv/aistack`. The module was never written, here or elsewhere.

**Resolved 2026-08-23** by removing `src/aistack/funnel/`. The owner's
reading: a CLI whose implementation was never committed is not a deferred
feature, it is a fragment. What it described is preserved in the commit and
in this entry — bytes through an integrity-checked ASCII envelope, `pack` /
`unpack` / `verify`, with a SHA-256 the receiver can check — so an idea that
returns starts from a specification rather than from an orphan front end.

The immediate effect is on OS-001: the inventory imports cleanly, so the
orphan count stopped being an upper bound and became a count.
**Derivable** yes — importing every module and reporting the failures is
exactly what found it, and `contract-debt` now does that continuously
**Qualification** none required; the decision was taken 2026-08-23.

#### GOV-0002/OS-006 — `PRINCIPLES-REGISTRY.md` does not follow `<ID>-<Title>.md`

**Nature** `non-conforming` · **Opened** 2026-08-21 · **State** resolved 2026-08-23 by the rename to `FDN-0012`
**Observed** It declares `id: FDN-PRINCIPLES` and its filename carries no
title, while STD-0102 mandates the pattern. Invisible to every pass until
2026-08-21.
**Resolved 2026-08-23.** The owner chose to rename both the file and the
identifier rather than declare an exception. `FDN-PRINCIPLES` became
`FDN-0012` — the next free number — and the file became
`FDN-0012-AIStack-Principles-Registry.md`. This is the second deliberate
exception to *"identifiers never change"*, after the `<DOMAIN>-P-NNN`
renumbering of 2026-08-21, and like that one it is bounded and recorded
rather than silent.

**Closing it exposed OS-020.** Five artifacts declared
`- PRINCIPLES-REGISTRY` in `relations: references:` while the registry's
identifier was `FDN-PRINCIPLES`. Those five references designated nothing,
in the Manifesto and in three Foundation documents, and no check compares a
declared reference against the set of declared identifiers. They were
corrected with the rename.
**Derivable** yes — a check comparing filename to `id` and `title`
**Qualification** none required; the decision was taken 2026-08-23.

#### GOV-0002/OS-002 — The tool that measures contract debt is not in the product

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** resolved 2026-08-22 by `4010d1f`
**Observed** `tests/unit/kernel/contracts/conformance.py`, written 2026-08-21
for four kernel contracts. It is the only code that can decide whether a
class satisfies a Protocol structurally, and it lives in the test tree.
**Resolved 2026-08-22**, in three steps that had to happen in that order:

1. `aistack.conformance.structural` — the structural comparison, promoted
   out of the test tree.
2. `aistack.conformance.inventory` — the discovery that did not exist: walk
   the package, separate contracts from concrete classes, compute what
   nothing satisfies.
3. `contract-debt` — the eighth integrity check, publishing what the
   projection carries.

The owner chose publication **inside the projection** rather than through a
separate command. `IntegrityCheck.evaluate` still observes a `ContextBundle`
and the contract is untouched; the archive gained a fifth entry,
`contract-inventory.json`, and the bundle format moved to 1.2. The
consequence is the point: an agent handed the bundle and nothing else can
state the contract architecture of the heritage it received, which is what
VS-2 asks of a projection.

Findings are `OBSERVATION`. `is_clean` ignores those — *they state facts
that are not yet governed rules* — so STD-0300 criterion 2.6, engraved the
same morning, holds on a heritage carrying twenty of them. Raising them
would have been a check inventing a verdict STD-P-002 refuses.
**Derivable** no — this is what makes `contract-debt` derivable
**Qualification** none required; the decision was taken 2026-08-22.

#### GOV-0002/OS-008 — Ten directories under `src/aistack` have no `__init__.py`

**Nature** `non-conforming` · **Opened** 2026-08-22 · **State** resolved 2026-08-22 by the ten `__init__.py` files
**Observed** `funnel`, `integrity`, `integrity/checks`, `core`, and five
under `transaction/`. ADR-0001 decision 4 states that such directories
*become proper Python packages*. Verified 2026-08-22: this breaks neither
import nor packaging — the built wheel contains all of them — but it does
break `pkgutil` discovery. Concrete cost: two measurements of OS-001 silently
did not see the integrity validator.

**Resolved 2026-08-22** by adding the ten files. Discovery went from 252
modules to 294, and the wheel still ships 295 `.py` files — measured on the
built artifact, not read from `pyproject.toml`. The blind spot covered 33
files, `src/aistack/integrity/` among them: the tool that validates the
heritage was invisible to the tool that inventories it.

Adding them immediately exposed OS-018, which the blind spot had been hiding
for five weeks. That is the argument for closing a blind spot before
measuring through it.
**Derivable** yes — a check over the source tree
**Qualification** none required; ADR-0001 already decided it.
