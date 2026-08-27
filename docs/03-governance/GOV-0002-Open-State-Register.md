---
artifact:
  id: GOV-0002
  title: Open State Register
  type: Governance Register
  semantic_type: Knowledge Artifact
  domain: Governance
  criticality: C2
  confidence: Declared
  version: 1.58
  status: Draft
  owner: Foundation
  created: 2026-08-22
  updated: 2026-08-27

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

## What a closure must carry

Two rules, adopted 2026-08-27 by the owner. Both come from entries that closed
wrongly on the day they were written.

### A condition about the world outside this repository cites its measurement

Inside the repository the suite and the projection *are* the measurement: an
entry closing because a check exists closes against a check that runs. Outside
it — a host, a mirror, a forge, a published image — nothing runs, and the
closure states what was measured and when.

GOV-0002/OS-012 closed on *nothing on any host still declares it*, which is a
condition about a host, and nobody looked. OS-011 and OS-032 are the same
shape and were the same risk.

The rule is deliberately narrow. A closure citing a measurement for everything
would produce citations for the sake of citing, and a formal citation nobody
can falsify is the defect this register keeps finding rather than a protection
against it. That is also why this is prose and not a check: `register-coherence`
could require a resolved entry to carry a date and a command, and could not
tell whether either was true.

### A closure names what still asserts the condition

An entry states a condition of the system, and the heritage usually says the
same thing elsewhere in its own words. Closing the entry does not close those
sentences.

GOV-0002/OS-028 closed the two-spelling divergence on the morning of
2026-08-27 **and cited its measurement** — the rule above was satisfied.
OPS-0002 § *The canonical name* went on describing that divergence as current
until the evening, on three forges, in a C2 artifact revised three times that
afternoon. The closure was right and the heritage was wrong.

So a closure names the artifacts that carried the condition. Producing the
list is a `grep` — *who else says `AISTack`?* — and the value is in having to
ask rather than in the list.

**A check on citations would not have caught it.** The failing paragraph did
not cite OS-028; that is why it survived. What is derivable is the sentences
that name an entry, and the sentences that matter are the ones that do not.

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

#### GOV-0002/OS-039 — The Selection Engine is implemented and consumed by nothing

**Nature** `contract-debt` · **Opened** 2026-08-27 · **State** open
**Observed** measured 2026-08-27 across the whole repository, while giving
ADR-0003 the implementation table STD-0100 v2.6 requires:

```text
SelectionEngine        → 0 callers, 0 tests
ByIdsSelectionStrategy → 1 instantiation, in bootstrap, with an empty list,
                         registered as `by-ids` and never retrieved
```

`selection_ui/app.py` imports `Selection`, the model, not the engine.
`docker_selection_catalog` builds a `SelectionCatalog` and writes JSON without
passing through the engine or `CatalogView`. `kernel/selection/__init__.py`
does not export the engine at all.

**The delegation ADR-0003 decides is complete for one criterion**, and that is
not the finding. The finding is that nothing calls it, and that **no
instrument sees it**: `contract-debt` does not count `SelectionStrategy`,
because `ByIdsSelectionStrategy` satisfies it, and `SelectionEngine` is not a
contract — so a Protocol with an implementation and no consumer measures as
healthy.

*ADR-0003's own prose said something narrower and said it since 2026-08-21:
four of five criteria have no strategy. That is a coverage gap. This is a
different condition, and the difference only appeared because the section was
**re-measured** rather than converted into a table.*
**Derivable** partly, and not by anything that exists. That a class has no
caller is measurable — `contract-debt` measures the neighbouring question and
would need a second dimension, *consumed by*, which OS-001 named as one of the
three that place a contract and which nothing computes.
**Qualification** `unknown`. The three readings that were live on 2026-08-27:

- **it is a moving part waiting for its caller.** `docs/99-meta/roadmap/`
  carries *Selection Engine Completion*, and STD-P-002 puts specification
  before implementation. Then this is early rather than orphaned — and the
  roadmap is outside the projection, which is exactly how ADR-0009's two
  unfinished consequences survived five days (OS-035);
- **it is an unearned abstraction.** ARC-P-006, and the same reasoning that
  removed three day-one protocols and `KnowledgePipeline` on 2026-08-27 under
  OS-001. The counter-argument is on the record: that pass nearly deleted
  `discover` for exactly this reason and was wrong;
- **the consumer is the missing piece and it belongs elsewhere.** Nothing in
  this repository selects anything today; `selection_ui` persists selections
  made by a human. The engine may be waiting on a surface rather than on a
  caller.

*Opened on the owner's decision of 2026-08-27, in preference to a fifth table
row — nothing calling the engine is not a step of a decision that commits to
the engine delegating.*

---

# Non-conforming instances

None open. OS-006, OS-007, OS-021, OS-023, OS-024, OS-028 and OS-036 are in
*Resolved*.

Three of those seven closed by **retiring or narrowing the rule** rather than
by conforming to it. A heritage that only ever fixed instances would end with
rules nothing could satisfy.

*Emptied twice on 2026-08-27: once in the morning, refilled the same afternoon
by OS-036, and emptied again by the rule OS-036 produced.*

---

# Defects

None open. OS-009 and OS-010, the two defects of `sync_mirrors.sh`,
were resolved on 2026-08-23 and are in *Resolved*.

An empty section is kept rather than removed: a register with no defects
section could not be told from one that never looked for any.

---

# Published artifacts

None open. OS-011 and OS-037 are in *Resolved*.

An empty section is kept rather than removed, for the same reason as
*Defects*: it states that this heritage publishes artifacts and currently
has none in a doubtful state, which is not the same as a register that never
thought to look.

---

# Risks

None open. OS-012, the only entry of this nature, was resolved on 2026-08-27
by retiring `aistack-backend` — six days after the exposure was recorded and
four after its retirement was decided.

The exposure is discharged: nothing answers and no image exists. What that
closure asserted without measuring is OS-036, under *Non-conforming
instances*, and it is filed there rather than here because a declaration in an
archive is a rule violated and not a door left open.

---

# Decisions

None open. OS-003, OS-013, OS-014, OS-015, OS-022, OS-034 and OS-038 are in
*Resolved*.

**Every section of this register was empty on 2026-08-27**, for the first time
since it was written on 2026-08-22 — *and it lasted about forty minutes.*

That paragraph read *every section of this register is empty*, in the present,
and OS-039 was opened the same evening by the first of the eight measurements
STD-0100 v2.6 had just made obligatory. It is corrected here rather than
quietly, because it is the fourth time in one day that a sentence true when
written stopped being true — § *What a closure must carry* was written that
afternoon for exactly this.

*What was said then still holds, and is why the emptiness was worth so little.*
A register with nothing open means every known condition has been qualified,
not that none exists. The projection kept counting through it, and the first
ADR anyone re-measured produced an entry.

---

# Resolved

An entry moves here with the date and what discharged it, and is never
deleted. A register that erased what it had closed could not show that a
rule ever bound anything.

#### GOV-0002/OS-038 — Eight accepted decisions say nothing this heritage can read about their implementation

**Nature** `decision` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by STD-0100 v2.6 and OPS-0002 v1.7
**Observed** measured 2026-08-27 across the nine accepted ADRs, while scoping
`unfinished-decisions`:

| Form | Count | Which |
|---|---|---|
| an implementation table | 1 | ADR-0009 |
| the same knowledge in prose | 2 | ADR-0003, ADR-0005 |
| nothing at all | 6 | ADR-0001, ADR-0002, ADR-0004, ADR-0006, ADR-0007, ADR-0008 |

**The two prose sections both declare undone work, and neither is in this
register:**

> ADR-0003 — *four of the five criteria this ADR anticipates have no strategy
> yet.*
>
> ADR-0005 — ***The migration below has not happened.** […] One step of it
> remains.*

`undated-assertions` does not see them: *yet* and *has not happened* are not
among its four markers, and adding them was measured and declined when that
check was written.

The six that declare nothing are the larger half. **An accepted decision
silent about its implementation is not a decision that was implemented** — it
is one nobody has asked about since the day it was accepted, and this heritage
has no way to tell the two apart.

**Resolved 2026-08-27.** Both questions answered by the owner:

- **yes**, an accepted decision declares its implementation state in a form
  this heritage can read — STD-0100 v2.6;
- **`unfinished-decisions` rises to `WARNING`**, and rises **in the commit
  that brings the count to 0 of 9**, not before.

**The sequencing is the substance of the second answer.** Raising it earlier
would state that the heritage is non-conformant while OPS-0002 § 1 makes
`clean: True` a condition of publishing — so the rule would forbid publishing
the eight commits that repair it. **A rule that blocks its own repair enforces
nothing; it only stops the work.**

That produced a rule of its own rather than an exception for this case:
**OPS-0002 v1.7 § 1 now admits a warning an open register entry names.** The
next check to be raised does not have to be raised last, and the entry is what
keeps the warning explained — a report carrying a warning nobody can account
for teaches its readers to scroll past warnings.

**This entry is `decision` by nature, and its questions are answered**, so it
closes on the answers rather than on the work. What remains is execution, and
it is **published rather than filed**: `unfinished-decisions` reports the count
at every projection, recomputed, where an entry would be a sentence nobody
recalculates. The precedent is exact and same-week — `contract-debt` publishes
13 of 50 at every run and OS-001 closed on 2026-08-27.

*Per § What a closure must carry, second rule: three sentences outside this
register said this entry stays open — STD-0100 v2.6, the check's own docstring,
and a test docstring. All three are corrected in the same act. It is the second
closure to produce that work and the first where the grep found something in a
test.*
**Derivable** yes, once the form is decided. That an accepted ADR carries a
table with terminal states is checkable; that a prose paragraph means *undone*
is not.
**Qualification** `unknown`. One question, and it is about the ADR format
rather than about a check:

- **must an accepted decision declare its implementation state in a form this
  heritage can read?** Yes means nine artifacts to touch and a governed table
  format, with the positional fragility `principle-identifiers` and
  `register-coherence` both carry. No means `unfinished-decisions` protects
  one ADR of nine and the other eight rely on someone remembering.

*Opened rather than folded into the check, on the owner's decision of
2026-08-27. The measurement is worth more than the check it was taken for, and
a blind spot recorded only in a docstring is a blind spot nobody reviews.*

**Decided 2026-08-27 by the owner: yes.** An accepted decision declares its
implementation state in a form this heritage can read — a table of steps and
terminal states, declared in STD-0100 v2.6 § *An accepted decision declares
its implementation state*.

`unfinished-decisions` gained the second half the same day and **the gap is
now published rather than described**: 8 of 9 accepted decisions declare no
implementation state this heritage can read, at every projection.

*The check reports it at `OBSERVATION` and not `WARNING`, deliberately and
temporarily. `clean: False` would block publication under OPS-0002 § 1 — which
means it would block publication of the very commits that fill the eight.
**Raising it once they declare is a decision of its own and stays with this
entry.***

**Both questions were answered the same day, and this entry closes on
that** — see the resolution below.

*What it will cost is not hidden: eight ADRs read, and for each one the three
measurements OS-001 established — what implements the decision, what consumes
it, and what governs it. Any one alone gives a confident wrong answer, and
this register has that mistake twice.*

#### GOV-0002/OS-035 — Two consequences of ADR-0009 were never built

**Nature** `contract-debt` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by ADR-0009 v1.8 and `unfinished-decisions`
**Observed** ADR-0009 was accepted on 2026-08-22 with two steps left, and its
implementation table carried them as *not started* for five days. Retiring
`aistack-backend` on 2026-08-27 discharged the exposure and left both:

- **`runtime_ui/`, the web surface.** § 6 promises *iso-usage on capability*,
  and the capability survives through the CLI — a global diagnostic, one
  container named, and the runtime catalogue. What does not survive is the
  interaction: there is no web surface, and there was one.
- **The three-state qualification.** § 6 states that the experimenter's state
  icon is *corrected rather than reproduced*, because
  `health.get("Status", "healthy")` displays a container with no healthcheck
  as healthy, and FDN-0003 Article 12 requires healthy, unhealthy and
  undeclared. Measured 2026-08-27: **nothing implements those three states.**
  `DockerRuntimeCatalogBuilder` carries Docker's raw `state` and `status`.

The second is the sharper one. A correction that a C2 ADR announces and
nothing performs is not a missing feature — it is the heritage stating that a
defect was fixed when it was only described. The experimenter is gone, so the
wrong icon is gone with it; what remains absent is the right one.

*This entry exists because a table cell reading `not started` is not an open
state. It sat in ADR-0009 from 2026-08-22 to 2026-08-27 and nothing surfaced
it — the register did not know, and the projection publishes nothing about an
ADR's unfinished rows.*

**Resolved 2026-08-27.** All three questions answered, and each by a different
kind of act:

- **the web surface is abandoned** — ADR-0009 § 6, and the implementation row
  reads `abandoned — 2026-08-27` rather than a sentence meaning *one day*;
- **the health qualification is built** — `ContainerHealth` and `health_of`
  derive health from what `docker ps` publishes, a missing verdict yields
  `undeclared`, and the runtime catalogue carries it beside the status it came
  from. The retraction came first, on its own, because it was true the moment
  it was written and the implementation was not;
- **the third produced a check and an entry** — `unfinished-decisions`, and
  GOV-0002/OS-038 for the eight accepted ADRs it cannot reach.

**The defect was measured before it was repaired**, which this entry did not
do when it was opened: 44 of 61 containers on the reference deployment declare
no healthcheck, and every one was displayed as sound. Seventy-two per cent.
This entry had said *nothing implements those three states*, which was true
and said nothing about what it cost.

**A fourth state was added**, on the owner's decision of 2026-08-27:
`starting`, for a healthcheck declared whose verdict has not returned. The
measurement found none of it, and zero is an instant rather than an absence —
the state is transitory, and every healthy container passes through it on each
restart. Widening a vocabulary is a separate act, which is why it is recorded
in ADR-0009 v1.8 § 6 and not only in the code.

*Per § What a closure must carry: this condition lives inside the repository,
so the suite and the projection are its measurement — 596 tests, seventeen of
them on this vocabulary, and a mutation pass that removed each invariant and
watched a test fail. The parentheses of the pattern survived theirs and are
now watched by a test that says it asserts a boundary rather than a defect.
What still asserted the old state: ADR-0009 § 6 itself, corrected in the same
act, and nothing else — `health.get` appears nowhere in this heritage; it was
the experimenter's, and the experimenter is gone.*
**Derivable** partly. That no code computes three health states is measurable
and was measured by reading. That an ADR's implementation table still holds
undone rows is derivable and nothing derives it.
**Qualification** `unknown`. Three questions, and they are not one:

- **is `runtime_ui/` still wanted?** The capability is reachable from the CLI
  and the experimenter it replaced is retired. A web surface may now be a
  preference rather than a consequence;
- **the three-state qualification is not optional in the same way.** It is a
  correction ADR-0009 announced against FDN-0003 Article 12, and it stands
  undone whether or not anything displays it;
- **should an ADR's unfinished rows reach this register automatically?**
  Five days of *not started* passed unnoticed, and the same shape produced
  OS-012 — a retirement decided on 2026-08-23 and done on 2026-08-27 only
  because something else made it visible.

**The third is decided 2026-08-27 by the owner: a check, restricted.**
`unfinished-decisions` reads the implementation table of an accepted ADR and
observes every row in no terminal state — `done`, `abandoned`, `superseded`.
`OBSERVATION`, because STD-P-002 puts specification before implementation and
an unfinished row is not a fault; what was wrong is nobody being told.

**Its reach was measured before it was written, and it is small.** Of nine
accepted ADRs, one carries a table. Two carry the same knowledge in prose and
are invisible to it. Six declare nothing at all. GOV-0002/OS-038 carries those
eight, because a check whose blind spot is unwritten reads as coverage.

**The first is decided 2026-08-27 by the owner: `runtime_ui/` is abandoned.**
ADR-0009 § 6 says so and says why — *iso-usage on capability*, not on
surface, which is the reading that already permitted retiring
`aistack-backend` without its replacement. The three measured interactions
are reachable from the CLI; what is lost is the interaction, and it had one
user.

The implementation row reads `abandoned — 2026-08-27` where it read *not
built, and not a blocker*. **That is the substance of the decision, not its
bookkeeping**: a row in a terminal state is a row nobody has to re-read,
where a row that means *one day* is an open state filed in a place this
register cannot see. OS-034 was closed the same way on 2026-08-27.

**The second is decided 2026-08-27 by the owner: retract, then implement.**
ADR-0009 v1.5 § 6 stops asserting a correction nobody performed — it read
*are corrected*, in the present, for five days. The retraction is worth its
own step because it is true the moment it is written, where the
implementation is not; the same order was owed to STD-0100 on 2026-08-22 and
to OPS-0002 § *The canonical name* on 2026-08-27, and paid neither time.

What is left here is the implementation: three health states, computed, where
`DockerRuntimeCatalogBuilder` carries Docker's raw `state` and `status`.

*It was emptied on 2026-08-27 — the nature that carried nine entries this
week, including OS-001, held nothing for the first time since the register
was written on 2026-08-22 — and refilled the same hour by the entry above.*

#### GOV-0002/OS-037 — A published procedure described a divergence that had been closed

**Nature** `published` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by OPS-0002 v1.6 and GOV-0002 § *What a closure must carry*
**Observed** OPS-0002 § *The canonical name* read, from its first version on
the morning of 2026-08-27 until v1.6 that evening:

> *Read off the publication output of 2026-08-23, and still true as of
> 2026-08-27: the repository is addressed as `AISTack` on Codeberg and in the
> publisher's `origin`…*

GOV-0002/OS-028 closed that divergence earlier the same day — the Codeberg
repository was renamed and the publisher's remotes corrected, verified through
each forge's API. Read off the publication output of 2026-08-27 at 15:02, all
four routes name `AIStack`.

The artifact is C2 and reached the SPOT and both mirrors carrying the
sentence. It was revised three times that afternoon — v1.3, v1.4, v1.5 — and
the section was re-read on none of them.
**Derivable** no, and the reason is the entry. `undated-assertions` exists for
exactly this shape and passes it: the sentence carries a date and the date was
right. **A date is not a measurement.** A citation check would not have caught
it either — the paragraph never cited OS-028, which is why it survived.
**Qualification** **decided 2026-08-27 by the owner.** A closure names the
artifacts that carried the condition it changes. GOV-0002 § *What a closure
must carry*, second rule.

**Resolved 2026-08-27.** OPS-0002 v1.6 carries the correction and the
measurement. The rule is written so that the next closure has to ask the
question this one did not.

#### GOV-0002/OS-036 — `aistack-backend` is still declared where its retirement was recorded as complete

**Nature** `non-conforming` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by GOV-0002 § *What a closure must carry*
**Observed** OS-012 was closed on 2026-08-27 against the condition OPS-0002
v1.3 states in its own words — *a component is retired when nothing on any
host still declares it*. **Nothing measured that condition.** The container
was stopped and the image removed; what declared them was asked afterwards,
by which time the Compose label that answers it had gone with the container.

The recovery search named exactly one file:

```text
/srv/aistack/docker-compose.yml
```

`docker compose ls` lists no `aistack-backend` project among the 34 running,
so nothing runs from that declaration. What survives is the declaration
itself: the service block is intact, and one `docker compose up` in that
directory rebuilds an unauthenticated API holding a writable Docker socket.

The file is the ancestor's, which FDN-0005 declares an archive.
**Derivable** no. This heritage describes a product and not a host (OS-015),
and reads no compose file outside its own tree. What *is* derivable is the
closure: an entry that names a condition and cites no measurement of it.
**Qualification** `unknown`. Two questions, and the second outlives the first:

- **what happens to the service block?** Removing it edits an archive, which
  FDN-0005 permits — *whatever still lives in the ancestor migrates here or
  ends there* — and `aistack-origin` holds the history either way. Leaving it
  keeps a file that describes what the ancestor was, and keeps `docker compose
  up` one command away from restoring the exposure;
- **may an entry close on a condition nobody measured?** OS-012's closure
  quotes the rule and cites no measurement. Nothing in this register requires
  one. The entry that refused hardest to close early — it stayed open four
  days on the argument that a written obligation retires nothing — is the one
  that closed on an assumption.

**The first is decided 2026-08-27 by the owner: the discovery path is
removed.** And it was measured first, which is the whole of what changed
between this decision and the one that produced the entry. A sweep of every
running container's `com.docker.compose.project.config_files` returned exactly
one path under `/srv/aistack`:

```text
/srv/aistack/AIStack/docker-compose.selection-ui.yml
```

Inside the governed repository. Nothing alive descended from the ancestor's
compose, and it was moved to `docker-compose.yml.archived`.

**That removes a default and not a capability.** `docker compose -f
…/docker-compose.yml.archived up` still works; what has ended is `docker
compose up` typed in that directory, which is the shape the exposure would
have come back through. An archive is read, and a file Compose finds by
walking is not being read.

Recorded this way rather than as *done*, because the difference between the
two sentences is the subject of the second question.

**The second stays open, and this entry stays with it.**

**Resolved 2026-08-27.** GOV-0002 § *What a closure must carry*, first rule: a
condition about the world outside this repository cites its measurement. The
second question is answered — not by permitting the closure that produced this
entry, but by requiring of the next one what this one lacked.

The first question was decided and executed the same day, above. Both halves
are discharged.

*The rule is narrower than the question was. It does not say an entry may
never close on judgement. It says that where the condition lives on a host, a
mirror or a forge, judgement is not available to whoever reads the entry
later.*

**What still asserted the condition**, per the second rule, applied to this
closure rather than described by it. Three sentences outside this register
name `aistack-backend`:

| Where | Reading |
|---|---|
| OPS-0002 § *Retiring a component*, two bullets | records of what happened, in the past tense — left as written |
| ADR-0009 § *What the retirement delivered* | written after the retirement — accurate |
| ADR-0009 § *Context*, first sentence | **read as current and was not** — *has been running on this deployment* |

The third is corrected in ADR-0009 v1.7, and corrected the way the compose
file was earlier the same day: the sentence stays as the decision was taken,
and a dated note says the section describes 2026-08-22 and is not rewritten
as the situation moves. A decision's context is evidence of what was known,
not a claim about the present.

*The grep took one command. It is written down because the rule is worth
exactly what the first person to skip it makes it worth.*

**A fourth instance, found the same evening by the habit rather than by the
rule.** `src/aistack/integrity/checks/reference_integrity.py` carried, in a
docstring: *`KnowledgeArtifact.id` is not the governed identifier — the builder
sets it to the content hash […] recorded as GOV-0002/OS-021*. OS-021 was
closed on 2026-08-23 by keying artifacts on their identifier; the field has
carried the declared identifier since, and `register-coherence` selects on it.
The sentence was false for four days, inside a check written to compare what
artifacts declare.

It is recorded here rather than in an entry of its own because it is the same
condition OS-037 states, in a fourth location: **the closure of an entry does
not close the sentences that agreed with it.** Corrected in place, with what
survives the correction — the reason this check reads `content` and not the
model — kept, because that reason was always the real one.

*The rule was adopted hours earlier and this was found by following it out of
habit rather than by applying it to a closure. A rule that only works when
someone remembers to invoke it is worth what OS-038's last question is worth.*

*Six entries of this nature closed before it: OS-006, OS-007, OS-021, OS-023,
OS-024 and OS-028, all in* Resolved. *Three of the six closed by retiring or
narrowing the rule rather than by conforming to it — a heritage that only ever
fixed instances would end with rules nothing could satisfy. This one is the
opposite case: the rule is three hours old and the instance is the run that
followed it.*

#### GOV-0002/OS-012 — `aistack-backend` exposes an unauthenticated API holding a writable Docker socket

**Nature** `risk` · **Opened** 2026-08-21 · **State** resolved 2026-08-27 by retiring the component
**Observed** `GET /api/docker/containers` answers 200 with no credentials,
and `[ -w /var/run/docker.sock ]` is true inside the container — which is
root on the host. Until 2026-08-21 it also sat on the `proxy` network with 43
containers including WordPress. Mitigated the same day: bound to
`127.0.0.1:8010`, removed from `proxy`, verified unreachable by name from
another container. **The API itself is unchanged.**
**Derivable** no
**Qualification** **decided 2026-08-23 by the owner.** Neither authenticate
nor accept: **retire the component.**

*This entry was not closed by the rule OPS-0002 v1.3 states, and the departure
from what was proposed is deliberate. A rule saying that a retirement includes
its deployment does not retire anything. `aistack-backend` still answers an
unauthenticated API holding a writable Docker socket; closing the entry
because the obligation is now written would be the false closure this register
exists to prevent. It closes when the component stops running.* ADR-0009 already decides the migration
of `aistack-backend`'s function, and authenticating something scheduled for
removal is work thrown away.

The remainder of ADR-0009 therefore becomes the priority, and this entry
closes when the surface disappears rather than when it is defended. It stays
open until then; the mitigation of 2026-08-21 holds meanwhile — bound to
`127.0.0.1:8010`, off the `proxy` network.

**Resolved 2026-08-27.** The component is retired. An unauthenticated API
holding a writable Docker socket — root on the host — stopped existing six
days after it was recorded and four after its retirement was decided.

**It was retired without the web surface ADR-0009 § 6 anticipated**, and the
reading that permits that is the section's own title: *iso-usage on
capability*, not on surface. The three measured interactions are doable from
the CLI, and ADR-0009 v1.4 states which command replaces which.

What that leaves undone is GOV-0002/OS-035, and it is stated there rather
than carried in this entry: the web surface, and the three-state
qualification § 6 announced and nothing ever built.

**The order was inverted deliberately.** A surface that has not been built is
a smaller thing than a door that is open. The retirement discharges the
exposure; the two consequences remain, visible, in an entry of their own
rather than as a table cell reading *not started*.

*Per OPS-0002 v1.3 a retirement has a second half: the component is retired
when nothing on any host still declares it. This entry closes on that
condition and not on the decision — which is why it stayed open through the
four days between them, and why it was not closed on 2026-08-27 by the rule
that states the obligation.*

**Corrected 2026-08-27, hours after the paragraph above was written.** The
condition it invokes was never measured. `/srv/aistack/docker-compose.yml`
declared the service throughout, and the container had been removed before
anything asked what declared it — so the Compose label that would have named
that file went with the container. **GOV-0002/OS-036** carries the residue and
the two questions it raises.

What the retirement discharged is real and is left standing: no container
answers, no image exists, the exposure this entry recorded is gone. What was
asserted beyond the measurement is the completeness. The paragraph above is
kept unedited, because an entry that insisted at length on not closing early
and then closed on an assumption is worth more intact than corrected in place.

#### GOV-0002/OS-034 — A Runtime migration is announced in a docstring

**Nature** `decision` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by abandoning the migration
**Observed** `KnowledgeProvider` describes itself, in code:

> *Backward-compatible discovery provider. This protocol remains compatible
> with the current Runtime. **The legacy `collect()` method will be removed
> once the Runtime migrates to the Discovery model.***

So there is a migration: from `collect` to `discover`, of the Kernel Runtime,
with a contract already shaped for the destination. `DiscoveryProvider`
declares `discover`; `KnowledgeProvider` extends it with the legacy
`collect`; the two providers that exist — `ComposeProvider` and
`DockerProvider` — implement `collect` and not `discover`.

**No artifact of this heritage says any of that.** FDN-0002 defines a
*Knowledge Provider* as *responsible for discovering observations […] they
only collect evidence*, using both verbs for one activity and settling
nothing. No ADR decides the migration, nothing dates it, nothing says what
would make it complete.

It was found on 2026-08-27 while qualifying OS-001, and it reversed the
qualification in progress. The agent had measured the glossary and the two
implementations, concluded that `discover` was an unearned abstraction, and
recommended narrowing the contracts to `collect` under ARC-P-006. The
docstring says the opposite: `collect` is what leaves. **The recommendation
was withdrawn before anything was written**, and the owner qualified both
contracts as planned instead.

FDN-P-004 makes knowledge the primary engineering asset. An intention that
lives in a comment is not one — and this one nearly caused the heritage to
delete its own destination.
**Derivable** no. That a docstring announces a migration is not detectable;
that the two providers implement the legacy method and not the target is,
and `contract-debt` publishes it as two orphans without saying why.
**Qualification** `unknown`. Two questions the owner must answer, and they
are separable:

- **is the migration still intended?** The docstring was written when the
  Discovery model was decided; nothing since names it. If it is not, then
  `discover` is unearned after all and the narrowing that was withdrawn
  becomes the right move;
- **if it is, where does it live?** An ADR deciding the Discovery model, or a
  line in ARCH-0012, or an entry here with what would end it. What may not
  continue is a Runtime migration whose only record is a comment in the
  contract it targets.

**Resolved 2026-08-27.** The owner abandoned it, on the measurement the first
qualification lacked.

Six call sites use `collect`. **None use `discover`** — and
`aistack.cli.docker_discover`, the command named after the model, calls
`collect` too, emitting the raw observation that FDN-0002 calls discovering.
Five weeks after the contract was shaped for the destination, the Discovery
model existed in two contracts, a registry's type parameter and a command
name, and in no behaviour.

`KnowledgeProvider` now declares one method, `collect`, over the `Provider`
identity. `DiscoveryProvider` is removed, and `ProviderRegistry` is typed on
what it actually holds — it was typed on the half nothing implemented, so its
declared element type was satisfied by nothing it could ever contain.

`ComposeProvider` and `DockerProvider` satisfy the contract that describes
them. The debt goes from 51 contracts and 15 orphans to **50 and 13**.

**This is the recommendation the agent withdrew two hours earlier**, and the
withdrawal was right at the time. It had measured the glossary and the two
implementations and concluded `discover` was unearned; the contract's own
docstring said the opposite, and a recommendation contradicted by its subject
is worth nothing. What returned it was the third measurement — the callers —
which is the dimension OS-001 records as missing from the first pass.

The word survives where it names the activity: FDN-0002's definition, and the
CLI command. What is retired is the second *method*.

#### GOV-0002/OS-001 — Twenty declared contracts are satisfied by nothing

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** resolved 2026-08-27 by qualifying every orphan

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

**Three were removed on 2026-08-27** — `KnowledgeEngine`,
`KnowledgeGenerator` and `KnowledgeRenderer`. Declared on the repository's
first day, never modified in seven weeks, implemented by nothing, consumed by
nothing but their own package re-export, and named by no artifact of the
heritage. ARC-P-006 says an abstraction is earned; these three never were.
The count went from 56 contracts and 20 orphans to 53 and 17.

**`KnowledgePipeline` and its registry were removed the same day**, as a
pair. The contract was consumed — `PipelineRegistry` typed its dictionary on
it, registered on it, returned it — so it was not mute like the three above.
It was half of a dead pair: a registry nothing constructs, not exported by
its own package, holding a type nothing implements. Removing either alone
would have left the other stranded.

Ten of the orphans are one family:
`PackageCapability` and its nine specialisations — `Compress`, `Decompress`,
`Encrypt`, `Decrypt`, `Hash`, `Serialize`, `Deserialize`, `Sign`,
`VerifySignature` — declared together and implemented never.

**`TransferTarget` was removed on 2026-08-27**, and the entry's earlier
account of it was imprecise. It said transfer code implements
`BundleTransfer` instead; measured, the contract it duplicates is
`BundleTransferConfiguration`, which declares `enabled`, `host`, `user` and
`destination_path` and *is* implemented. The two describe one knowledge item
— a transfer destination — differing by one field name, which is what
FDN-P-005 forbids. The superseded one went, with its contract test.

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

**Resolved 2026-08-27.** Every declared contract is now qualified, and the
figure the check publishes is 15 orphans of 51 contracts rather than 20 of 56.

| Contract | Qualification |
|---|---|
| `PackageCapability` and its nine specialisations | planned — 2026-08-23 |
| `Task` | planned — FDN-0002 § Task, cited by eight artifacts |
| `KnowledgePolicy` | planned — FDN-0002 § Knowledge Policy |
| `EvidenceCollector` | planned — ADR-0008's Knowledge Acquisition Dimension |
| `KnowledgeProvider` | satisfied since 2026-08-27 — OS-034 narrowed it |
| `DiscoveryProvider` | abandoned, removed — OS-034 |
| `KnowledgeEngine`, `KnowledgeGenerator`, `KnowledgeRenderer` | abandoned, removed |
| `KnowledgePipeline` | abandoned, removed with `PipelineRegistry` |
| `TransferTarget` | superseded by `BundleTransferConfiguration`, removed |

**Every qualification rests on a measurement, and two of them reversed the
answer that measurement first suggested.**

`KnowledgePipeline` was presented as approached by nothing, because the scan
looked for classes that *implement* each orphan and not for code that *uses*
them. `PipelineRegistry` used it. It was still removed, but as half of a dead
pair rather than as a mute contract, and removing it alone would have left a
registry typed on a deleted name.

`KnowledgeProvider` was nearly narrowed. The glossary and the two live
providers both pointed at `collect`, so `discover` looked unearned under
ARC-P-006 — until the contract's own docstring said `collect` is the legacy
method and `discover` the destination. The recommendation was withdrawn
before anything was written, and the migration it revealed is OS-034.

What the entry established beyond its own subject: a contract's position is
three measurements, not one — what implements it, what consumes it, and what
governs it. Any one of the three alone gives a confident wrong answer.

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

#### GOV-0002/OS-025 — The governed test command is not the command that works

**Nature** `contract-debt` · **Opened** 2026-08-23 · **State** resolved 2026-08-23 by ENG-TEST-0002 v2.2 and two declarations
**Observed** On 2026-08-23 the owner ran the governed command,
`source bin/aistack_env.sh && pytest -q`, on a shell where the virtual
environment was not active. `python3` was the system 3.12. The file printed
both of its warning lines and the suite ran anyway: 514 passed, and
`test_the_suite_runs_on_the_interpreter_the_heritage_declares` failed — the
test written the day before, catching the owner of the heritage that declares
it.

**This entry was opened on a claim that was false, and the correction is the
entry.** Its first version stated that *no artifact of this heritage names
the virtual environment, says where it lives, or says that it must be
active*. `scripts/dev-env.sh` does all three:

```
source "${PROJECT_ROOT}/bin/aistack_env.sh" || return 1
export PATH="${PROJECT_ROOT}/.venv/bin:${PATH}"
```

It names `.venv`, locates it under the repository root, puts it ahead of the
system interpreter, and reports which `python` and which `pytest` are in use.
It was written on 2026-08-21 and the agent had read this repository twice
that day without opening it.

**What is actually wrong is smaller and worse.** ENG-TEST-0002 is C3 and
states the standard test command as `source bin/aistack_env.sh && pytest -q`.
That is the half that declares the environment; `scripts/dev-env.sh` is the
half that completes it, and it sources the first, so nothing is bypassed by
using it. **The governed command names the half that does not finish the
job**, and that is precisely what was run and what failed.

Two further gaps were measured while establishing this, and they are the ones
that reach what ENG-TEST-0002 promises — *reproducibility, deterministic
execution, portability across environments*:

- **`pytest` is declared nowhere.** `pyproject.toml` configures it —
  `[tool.pytest.ini_options]`, carrying STD-0002's `testpaths` — and does not
  declare it as a dependency. The only declared dependency is `PyYAML>=6.0`,
  with no upper bound, and there is no lock file. `scripts/dev-env.sh`
  reports *where* pytest is; nothing states *which*. Two machines can run the
  same governed command against different versions of both and nothing would
  say so — the shape of OS-019 without even the warning.
- **Nothing compares the declared interpreter with the images.**
  `pyproject.toml` says `>=3.13`; `Dockerfile` and `Dockerfile.selection-ui`
  both say `FROM python:3.13-slim`; no test relates them. The existing test's
  own failure message reads *"the result says nothing about what the images
  run"* — and nothing checks what the images run.

The warning in `bin/aistack_env.sh` is deliberate and stays: the file is
sourced, so a `return` on a mismatch would drop the developer out of the
setup they asked for.
**Derivable** yes, for all three. Which command a C3 principle names is
readable; whether a configured tool is a declared dependency is readable; the
interpreter of a Dockerfile is one line.
**Qualification** **decided 2026-08-23 by the owner, after the entry was
corrected.** The standard command of ENG-TEST-0002 becomes
`source scripts/dev-env.sh`, which keeps declaring and providing in two files
— ADR-0001 leaves `bin/aistack_env.sh` the SPOT of the declaration, and the
other provides. `pytest` is declared as a development dependency, and a test
compares the declared interpreter with what both images ship.

The readings recorded before the correction — that the SPOT should activate
the environment itself, that the launchers should refuse, or that the
environment is deployment configuration — were all answers to a question that
did not exist. The environment was declared; the principle pointed at the
wrong file.

**Resolved 2026-08-23**, the three gaps together.

- **The command.** ENG-TEST-0002 v2.2 names `source scripts/dev-env.sh`.
  Declaring and providing stay two files, and two tests hold that boundary in
  both directions: the provider must source the declaration rather than
  restate it, and the declaration must not reach for `.venv`. A third
  compares the command the README shows with the one the principle names —
  they drifted before, three ways, which is what v2.0 was written to end.
- **The tool.** `pytest>=8.0` is declared under
  `[project.optional-dependencies] dev`. A floor and not a pin: there is no
  lock file, so it declares what the suite needs rather than what one machine
  holds.
- **The images.** A test reads `FROM python:X-slim` from both Dockerfiles and
  compares it to `requires-python`, in two assertions because they fail
  differently — the images can drift from the declaration together, or from
  each other after a partial edit.

Three mutations were applied and each killed a test: an image moved to 3.12,
the two images set against each other, and `pytest` removed from the
declaration.

*Placing `[project.optional-dependencies]` beside `dependencies` moved
`authors` and `license` into it — a TOML table header ends the table above
it. Caught by parsing the file rather than reading it, which is the same
method that disproved the packaging hypothesis in OS-001.*

#### GOV-0002/OS-003 — `ARC-P-005` and FDN-0011's second principle state one rule twice

**Nature** `contract-debt` · **Opened** 2026-08-21 · **State** resolved 2026-08-23 by registering `FDN-P-015`
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

**Resolved 2026-08-23.** `FDN-P-015 — The primary deliverable of engineering
is a governed set of contracts` is in the Foundation table. The count goes
from 50 to 51 and the register's last forward citation is gone.

**It required overturning a claim in a C3 artifact, and that is recorded
where the claim stood.** FDN-0012 v2.1 stated that registering both would
give one rule two SPOTs, *which FDN-P-005 forbids*. The owner was shown that
sentence before deciding — it had not been put in front of him when the
choice was first prepared, which is the defect in how the choice was
prepared, not in the choice.

The argument rested on holding the two for one knowledge item. They are held
to be two: `ARC-P-005` states an ordering, `FDN-P-015` states what
engineering delivers. The second implies the first and is not the first. The
v2.1 paragraph is rewritten rather than deleted, and quotes itself verbatim
before saying what replaced it.

What v2.1 was right about, and what stands: a principle restated in two
registered rows would be a duplicate. That is not what these are.

#### GOV-0002/OS-017 — A sentence about the code can become false and nothing sees it

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** resolved 2026-08-27 by `undated-assertions`
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

**Resolved 2026-08-27.** `undated-assertions`, the thirteenth check, at
`OBSERVATION` as the owner decided on 2026-08-23. It lists every line
carrying a marker without a date or a commit, at every projection — 19 when
it was written.

**Building it corrected the rule.** STD-0100 had listed six markers since
2026-08-22, written from intuition. Measured across the 66 artifacts:
`remains` accounts for 50 of 113 occurrences and `still` for 27, and reading
them shows why — they overwhelmingly introduce statements that hide no date
at all. *The repository remains the authoritative source of governed
knowledge* is not a dated claim. Keeping them would have published over a
hundred lines, and a report nobody can read is not a report. STD-0100 v2.5
carries four markers and the measurement that removed two.

**A quotation is not an assertion**, and the check knows it: the marker list
inside STD-0100, the ✗ example beneath it, and this register's own quotations
of the rule are all excluded by parity of emphasis, backticks and block
quotes. That is also why **no artifact is excluded by name** — excluding a
file for being noisy would be a check adapting to the data rather than to the
rule, and the register would have been the first candidate.

**The precision is stated rather than hoped for.** Roughly a third of the 19
are assertions that have gone or could go stale; the rest are rhetoric —
*Ollama today and another engine tomorrow* — or definitions. A reader scans
nineteen lines and decides. The check does not know which sentences are
wrong, and OS-017 said from the start that it could not: *the temporal
markers are detectable by pattern; whether the sentence carrying one is stale
is not.*

#### GOV-0002/OS-028 — The repository is addressed under two spellings

**Nature** `non-conforming` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by renaming the Codeberg repository and correcting the remotes
**Observed** Read off the publication output of 2026-08-23, and still true
on 2026-08-27:

```
workstation → https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack.git
publisher   → ssh://git@127.0.0.1:2222/fabrice.persiaut/AISTack.git
github      → bigbrother1969-bis/AIStack.git
codeberg    → bigbrother1969/AISTack.git
```

**The canonical spelling is `AIStack`**, decided by the owner on 2026-08-27
and declared in `pyproject.toml` under `[project.urls] Repository` — a
project fact, identical on every machine, which is why the Context Bundle
publishes `repository_url` from there rather than from any clone's remote.

Gitea tolerates case in repository names, so the SPOT answers to both and
**nothing has ever failed**. That is why it survived: a defect that produces
no symptom is found by reading, and nobody had reason to read four remote
URLs side by side until a publication chain was being written down.

Codeberg does not tolerate it. `bigbrother1969/AISTack` is genuinely a
differently-named repository from `bigbrother1969-bis/AIStack` on GitHub, so
the two mirrors of one SPOT carry two names.
**Derivable** partly, and half-derived. That `pyproject.toml` carries the
canonical name is asserted, and that OPS-0002 states the same one. What a
given clone's remotes are called is a machine fact and is not derivable from
the heritage — the same boundary as OS-015.
**Qualification** **decided 2026-08-27 by the owner.** Correct both, and
state the canonical name in OPS-0002 — done. **Two actions remain, and they
are on the owner's services rather than in this repository:** rename the
Codeberg repository to `AIStack` and update the publisher's `origin` URL.
The entry stays open until they are.

*Deliberately not enforced by `sync_mirrors.sh`. The owner weighed a check
comparing every remote against the declared name and chose not to: it would
add a warning to every publication for a defect that has never broken
anything, and remote names are machine facts.*

**Resolved 2026-08-27.** The Codeberg repository was renamed and the
publisher's `origin` and `codeberg` remotes corrected. Verified through each
forge's API rather than through the URL that was typed at it, because a
successful fetch proves nothing: Forgejo redirects a renamed repository, and
Gitea resolves a name whatever its case. The `name` field a server returns is
the name it holds.

```
codeberg  → AIStack
gitea     → AIStack
github    → AIStack   (never wrong)
```

**The directory holding the publisher's clone is deliberately left alone.**
It is a path, OPS-0002 states that the heritage governs roles rather than
machines, and renaming it would break two scheduled jobs that carry it
hard-coded — which is how those jobs were discovered at all.

#### GOV-0002/OS-029 — A date can be wrong at the moment it is written

**Nature** `contract-debt` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by a test against the git author date
**Observed** OPS-0002 was written on 2026-08-27 and dated **2026-08-23**
throughout — its frontmatter, its prose, and the two register entries created
with it. Seventeen occurrences in one patch, in a C2 artifact and a C2
register, published to the SPOT and both mirrors before anyone noticed.

The cause is not a typing slip. The agent carried the date from a
conversation record rather than reading a clock, across a four-day gap it did
not know had happened. `date` was available throughout, and three
independent sources disagreed with what it wrote: its own container, the
bundle identifier generated on the owner's workstation
(`aistack-context-2026-08-27`), and the `date` printed by
`scripts/sync_mirrors.sh` on the publisher.

**It was found by reading a terminal output, not by any check**, and by
comparing three clocks that happened to be in the same screen.

This is the sibling of OS-017 and not the same defect. OS-017 records a
sentence that was **true when written and became false**; the remedy there is
to carry a date. Here the date itself was false at the moment of writing, so
carrying one is exactly what went wrong. A rule that says *state your date*
is worth nothing if the date is assumed rather than measured — which is the
same failure as an allow list built from assumed prefixes (FDN-0012 v2.2), a
`.dockerignore` matching an assumed root, and a `PYTHONPATH` declaring one of
two source roots. Each looked exhaustive and covered a subset; this one
looked dated and was wrong.

Corrected on 2026-08-27. Where the artifacts refer to events of 2026-08-23 —
the HTTP 530, the false topology inference, the OS-015 ruling — those dates
were right and are kept.
**Derivable** partly, and the derivable half is worth having. An artifact's
`updated:` field can be compared with the commit that last touched the file:
a document claiming to have been updated four days before the commit that
wrote it is detectable in one pass over the projection and the log. Whether a
date *inside prose* is right is not derivable.
**Qualification** `unknown`. Two readings for the owner:

- **write the check.** Every artifact's `updated:` must not precede the
  commit date of its last change. It would have caught this patch before it
  reached the SPOT. It also fires on legitimate cases — a document edited
  across days, or a patch applied later than it was written, which is this
  project's normal delivery mode — so its severity would have to be
  `OBSERVATION` and its false positives accepted;
- **treat it as method rather than machinery**, and require the agent to
  measure the date at the start of every session, as it measures everything
  else before asserting it. That places the remedy where the defect was, and
  leaves nothing to catch a lapse.

**Resolved 2026-08-27**, by the first of the two readings: a test, not an
integrity check.

**It could not have been a check.** The Context Bundle carries `source_commit`
as a hash and no commit date, so nothing inside a projection can tell when an
artifact was written. The test lives in the integration suite and asks git.

**The rule is narrowed to revisions, and the narrowing was measured.**
Comparing `updated:` with the last commit to touch a file at all reports **31
of 65 artifacts** — mechanical sweeps touch files without revising them. A
rule accusing half of what it governs is not describing it, which is what
retired the file-name rule three patches earlier. Bumping the `version:` is
what makes an edit a revision, and under that reading the heritage held
**one** exception.

That one was real: `eb43842` moved ENG-TEST-0001 from version 1.0 to 1.1 on
2026-08-21 and left `updated: 2026-07-24`. A C3 artifact whose declared update
date preceded its own revision by four weeks, corrected here.

Three details each cost a measurement:

- **author date, not committer date.** `git format-patch` carries the author
  date and `git am` preserves it, so it means *when the artifact was written*
  on both machines. The committer date means *when the patch was applied* —
  later on every delivery this project makes, so reading it would fire on
  correct work and stay silent on the defect;
- **`--follow`.** Without it a rename reads as the whole file being added, and
  `ADR-0003` reported a revision it never had;
- **precedes, not differs.** A date *after* the last revision is legitimate —
  a typo fixed without a version bump. `FDN-0009` is that case, and an
  equality rule accused it.

The second reading — measure the date at the start of every session — is kept
as method alongside the test. The test catches at the workstation, before the
push; the method catches before the date is written at all.

#### GOV-0002/OS-022 — Parallel experimentation is a practice nothing declares

**Nature** `decision` · **Opened** 2026-08-23 · **State** resolved 2026-08-27 by FDN-0005 v1.2
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

**Resolved 2026-08-27.** FDN-0005 § *Experimentation*, a workspace beside the
nine already declared — which is what the practice always was, and what
nothing said.

It states three things and stops: that the space exists and is deliberate,
that a proof of concept enters the heritage by being written as an artifact
rather than by being found, and that an experiment carries an identifier and
a state which the heritage may cite before it is complete. **QUAL-0001 is
named there**, complete in execution and pending in evaluation, so that it
can be cited anywhere.

**What it deliberately does not decide** is written into the section itself:
the states a POC passes through, the criteria that make one integrable, and
who decides. Two observed cases justify declaring that the practice exists;
they do not justify fixing its procedure in advance. The paragraph saying so
is the record that it was left open on purpose.

#### GOV-0002/OS-013 — The ancestor's relation to the heritage is undecided

**Nature** `decision` · **Opened** 2026-08-21 · **State** resolved 2026-08-27 by FDN-0005 v1.1
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

**Resolved 2026-08-27.** FDN-0005 § *The ancestor*. Whatever still lives in
the ancestor migrates here or ends there, and `aistack-origin` is a permanent
backup rather than a second line of development. The migration of its
function stays with ADR-0009.

The ancestor is named there by its repository rather than by its path on any
machine — a filesystem location is a route, and FDN-0005 describes a product
rather than a host. That is the boundary of OS-015, applied while writing the
answer to a different entry.

#### GOV-0002/OS-014 — An installed AIStack cannot read the governed catalogue

**Nature** `decision` · **Opened** 2026-08-22 · **State** resolved 2026-08-27 by ADR-0009 v1.3
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

**Resolved 2026-08-27.** ADR-0009 § 7.1. A governed AIStack requires the
repository; an installed one is an executable without a heritage, and is
allowed to be — what it may not do is pretend to have one.

`docs/` is not shipped, `--catalogue` stays optional, and the failure stays
loud: a tool that silently qualified evidence against no catalogue would
report a clean deployment on an empty rulebook.


#### GOV-0002/OS-015 — Nothing declares which containers are expected to run

**Nature** `decision` · **Opened** 2026-08-22 · **State** resolved 2026-08-27 by ADR-0009 v1.3
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

**Resolved 2026-08-27.** ADR-0009 § 7.2, and it closes by declaring the
question out of scope rather than by answering it. This repository describes
a product; the set of containers one host expects describes that host, and
declaring it here would make every other installation contradict it.

`Signature.applies_to` remains, and remains deliberately a treatment of the
symptom. The gap is real and is now outside this repository rather than
pending inside it.

The same boundary was applied twice more on 2026-08-27 and held both times —
the machine publishing this repository to the public internet is unnamed by
the heritage, and OPS-0002 states the publication procedure in roles rather
than machines.


#### GOV-0002/OS-023 — `<ID>-<Title>.md` does not describe this heritage

**Nature** `non-conforming` · **Opened** 2026-08-23 · **State** resolved 2026-08-27 by retiring the rule
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

**Resolved 2026-08-27.** STD-0102 v2.3 retires the rule. A file name is not
governed: identity is `id`, declared in frontmatter, and where an artifact's
text sits is a convenience for whoever browses the tree.

No check was written and no file was renamed. The 25 keep their names, and
the three deliberate families — the `CMP-XXXX` components, the section
READMEs, the Manifesto — stop being non-conforming by being outside a rule
rather than by being excused from one.

**What the standard keeps** is the part that was never about file names:
*identifiers never change*, which governs `id`; and criticality does not
belong in a name, because it is a qualification that moves and would create a
second source for one fact.

It also keeps both corrections that preceded the retirement, and states that
they were right. OS-006 was an *identifier* change and cost five citations.
OS-007 was a rename that touched nothing. A file whose name contradicts its
declared title is still worth fixing when someone notices — what is retired
is the obligation, not the courtesy.

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

#### GOV-0002/OS-027 — The publication procedure is stated nowhere

**Nature** `contract-debt` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by OPS-0002
**Observed** The README declares the principle — the Gitea repository is the
SPOT, GitHub and Codeberg are publication mirrors and shall never be the
origin of governed knowledge — and no artifact said which role pushes where,
in what order, or what must hold before each step. Searched on 2026-08-27
across the README, `docs/` and ADR-0009: nothing.

**The cost was measured on 2026-08-23.** An agent read a `git remote -v`
listing, inferred a publication topology from it, and stated it confidently
and wrongly, because there was nothing to check the inference against. It
then retracted the reasoning while the conclusion happened to be right —
which is worse, not better, since only the owner could tell the two apart.

FDN-P-004 makes knowledge the primary engineering asset. A procedure that
lives in the owner's habits is not an asset; it is a dependency on one person
being available.
**Resolved 2026-08-27.** OPS-0002 — *Heritage Publication*, Operations, C2.

It states **roles rather than machines**: workstation, SPOT, publisher,
mirror. Which machine holds which role is deployment configuration and stays
out, which is the boundary the owner drew on 2026-08-23 in OS-015. One machine
may hold several roles; what the procedure fixes is the order.

It also records what 2026-08-23 established: that patches apply on the
workstation only, since applying them twice produces two commits for one
change; that the agent holds no role, because in its throwaway clone `origin`
is a mirror and publishing from it would invert the SPOT; and that a broken
public route to the SPOT does not reach the chain SPOT → mirrors, because the
publisher is co-located with it.

The three failure modes are written from occurrences rather than imagined —
the 530 of 2026-08-23, the rate-limited mirror of 2026-08-21 (OS-009), and
the script replaced by its own pull (OS-010).
**Derivable** no. A procedure is a decision about how people work.
**Qualification** none required beyond the choice of where it lives, which
the owner made: an artifact of its own rather than a section of the README or
of FDN-0005.

#### GOV-0002/OS-026 — Sourcing the declared environment twice declares it twice

**Nature** `defect` · **Opened** 2026-08-23 · **State** resolved 2026-08-23 by making both files idempotent
**Observed** `bin/aistack_env.sh` prepended the two source roots to
`PYTHONPATH` without checking whether they were already there, so every
source added them again. Six copies of each were visible in one working
session:

```
PYTHONPATH : .../src:...:.../src:...:.../src:...:.../src:...:.../src:...:.../src:...
```

`scripts/dev-env.sh` did the same with `.venv/bin` on `PATH`.

**It was found because ENG-TEST-0002 v2.2 made `scripts/dev-env.sh` the
governed command**, and that file prints `PYTHONPATH`. The report the
principle started naming an hour earlier is what exposed it — the instrument
found the defect on its first governed run, which is the argument for having
the environment describe itself out loud.

Harmless to imports: Python resolves the first match and duplicates only cost
a scan. Not harmless to the promise. ENG-TEST-0002 is C3 and asks for
*deterministic execution*, and a variable whose value depends on how many
times you sourced the source of truth is not deterministic. It also made the
only report of what is in use unreadable.
**Resolved 2026-08-23.** Both files remove their own previous entries before
prepending, so a shell already polluted is repaired by sourcing the file
again rather than by opening a new one.

Three tests run a real shell rather than reasoning about the files — a test
that read them would have agreed with their author. Three mutations were
applied; the second survived the first pass, because every run started from
an empty `PYTHONPATH` and de-duplication keeping the *first* occurrence was
then indistinguishable from one keeping the last. The variable is now seeded
before sourcing, and order is asserted: a developer with two checkouts who
sources one then the other must import from the second.
**Derivable** yes, and now derived
**Qualification** none required; a variable that grows on re-source is not a
judgement call.

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

#### GOV-0002/OS-032 — A component left the SPOT and its deployment stayed

**Nature** `risk` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by OPS-0002 v1.3
**Observed** `aistack-funnel-inbox.service` was enabled on the publisher and
had restarted **30 103 times**. Measured 2026-08-27:

```
Loaded: loaded (/etc/systemd/system/aistack-funnel-inbox.service; enabled)
Active: activating (auto-restart) (Result: exit-code)
Process: ExecStart=/srv/.../bin/aistack-funnel-inbox … status=226/NAMESPACE
        Scheduled restart job, restart counter is at 30103.
```

**It has never once started.** The first journal entry is `Jul 31 15:34:57`,
and it is the same failure as the last: systemd cannot set up the mount
namespace, because `ReadWritePaths` names a directory that does not exist. It
fails before reaching the executable — which does not exist either.

Neither path has ever existed in this repository. `bin/aistack-funnel-inbox`
and `docs/04-development/encapsulated-funnel/` have **no commit in the SPOT's
history**, none in the ancestor's, and nothing on disk under either. The unit
was installed on 2026-07-31 pointing at files that were never there.

The repository did hold a `funnel` package, and OS-018 removed it on
2026-08-23 because `aistack.funnel.__main__` imported a `core.py` that had
never been committed. So the picture is consistent and worse than a stale
unit: **a component whose code was half-committed, whose entry point was
never committed, and whose service was installed and enabled anyway.** The
committed half was removed four days ago; the deployment outlived it, and had
already outlived its own never-working state by three weeks before that.

**Nothing in this heritage could have seen it.** `runtime_diagnose` swept 62
containers on 2026-08-22 and published one finding. It looks at containers. A
systemd unit failing every five seconds on the machine that runs the
observation tool is outside its field of view entirely — which is OS-015 seen
from the other side. OS-015 says the heritage cannot tell *stopped because
broken* from *stopped on purpose*; this says it does not see this class of
object at all.

The service was disabled on 2026-08-27, which stops the loop and decides
nothing.
**Derivable** no, and the boundary is deliberate. OS-015 settled that this
repository describes a product rather than a host. What is arguably not host
knowledge is **the seam**: this unit names this repository's paths and exists
for its component, so the relationship between a component leaving the SPOT
and its deployment being retired is a fact about the project.
**Qualification** `unknown`. The immediate question is small — the unit is
for software that exists nowhere, so removing the file is the obvious end —
and the one behind it is not: **nothing connects the removal of a component
from the SPOT to the retirement of its deployment.** OS-012 is the same
question with the answer already chosen and the work not yet done; this is
the second instance in four days, which is the argument for stating a rule
rather than handling each case.

Whether that rule belongs in this repository at all is the prior question,
and it is the same one OS-015 answered *no* to. The difference a reader
should weigh: OS-015 concerned the expected state of a host, while this
concerns what the project owes a host when it removes something from itself.

**Resolved 2026-08-27.** OPS-0002 § *Retiring a component* states the rule the
owner chose: a component is retired when nothing on any host still declares
it, and removing the code from the SPOT is only the first half.

It is a procedure and not a check, deliberately. OS-015 settled that this
repository describes a product rather than a host, and the heritage reads no
service unit. What it can do is state that a removal has a second half, so
that whoever performs the first knows the work is not done.

The unit was disabled on 2026-08-27, which stopped the loop. Removing
`/etc/systemd/system/aistack-funnel-inbox.service` and reloading systemd is
the application of the rule, on the owner's host, and is not tracked here —
the register records conditions of the system, not a task list.

#### GOV-0002/OS-031 — Scheduled execution reports correctly to nobody

**Nature** `risk` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by OPS-0002 v1.2
**Observed** Two schedules run on the publisher, and until 2026-08-27 no
artifact declared either. Both were found by accident, while checking what
would break if a directory were renamed:

```
0 */6 * * *  scripts/maintenance/sync_context_bundle.sh   → regenerates the projection
0 0 * * *    scripts/sync_mirrors.sh                      → publishes the mirrors
```

The runs themselves are correct. `sync_mirrors.sh` refuses a working branch
and a dirty tree, reaches the SPOT before writing to any mirror, attempts
every mirror independently, and since 2026-08-23 exits non-zero when one
failed. **What it does not have is a reader.** Its output is redirected into
a file, so a failure that is unmissable in a terminal is a line nobody opens.

That is GOV-0002/OS-009 moved one step out. OS-009 was a run that stopped at
the first failure; this is a run that reports the failure correctly, to no
one. The exit code is right and nothing consumes it.

**A second fact, and it is the sharper one.** The six-hourly regeneration
invokes `python3` directly rather than sourcing `scripts/dev-env.sh`, so the
projection produced every six hours is generated by whichever interpreter the
host distribution installs. ENG-TEST-0002 is C3 and asks for reproducibility
across environments, and OS-019 measured what that axis costs: the same
contract inventory gave 20 orphans on one interpreter and 22 on another, at
the same commit. A projection regenerated four times a day outside the
declared environment is the one artifact of this heritage produced by an
interpreter nothing verifies.

Both facts are now stated in OPS-0002 v1.1. What to *do* about them is not.
**Derivable** no. The heritage cannot see a crontab, and OS-015 settled that
it does not try. What is derivable is the second fact's consequence — two
projections of the same commit carrying different inventories — and nothing
compares them today.
**Qualification** `unknown`. Two questions, and they are separable:

- **the unread report.** Options range from doing nothing — the schedules are
  a convenience and the manual run is the governed one — through mailing the
  failure, to having the daily run write its verdict where the next session
  reads it. Doing nothing is defensible and is what happens today; what is
  not defensible is leaving it undecided a second time now that it is
  observed;
- **the undeclared interpreter.** Making the six-hourly job source
  `scripts/dev-env.sh` is one line and would put it inside ENG-TEST-0002.
  Whether a scheduled regeneration is *validation* — which the principle
  governs — or mere convenience, is the owner's reading.

**Resolved 2026-08-27**, and the two questions got different answers, which is
why they were separated.

**The unread report: nothing, and it is written.** A schedule is a
convenience; the governed run is the manual one. Nothing depends on a nightly
publication having happened — the next manual run pulls the SPOT first and
publishes whatever the mirrors are missing. What that costs is a delay bounded
by the next person who publishes; what it buys is that no one has to read a
machine. A mailbox, or a verdict written where the next session looks, was
weighed and declined: it would add a thing to watch in order to protect a
thing nothing depends on.

OS-009 established that a run must *report* what it did, and it does. What was
decided here is who has to be listening.

**The interpreter: sourced, and the job refuses without it.**
`sync_context_bundle.sh` now sources `scripts/dev-env.sh` and exits non-zero
when the declared interpreter is not what it gets — verified by removing the
virtual environment, which produced `python3 is 3.11, this heritage is
verified on 3.13` and exit 1. A projection is a published artifact: a delayed
one is a nuisance and a doubtful one is a lie. That refusal goes to standard
error, which cron mails, rather than to the log file the other half of this
entry accepts nobody reads.

#### GOV-0002/OS-033 — Compiled bytecode can defeat mutation testing silently

**Nature** `defect` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by declaring `PYTHONDONTWRITEBYTECODE`
**Observed** On 2026-08-27, two tests of `undated-assertions` failed against
source that was already correct. The reported line numbers were off by one —
the signature of a mutation that had been reverted minutes earlier.

The cause is CPython's bytecode cache. A mutation pass rewrites a module and
re-runs the suite in under a second, which is faster than the filesystem
timestamp resolution the interpreter uses to decide whether its cached
`.pyc` is stale. It served the previous version.

**The direction that matters is the other one.** A mutation can appear to
*survive* when it was never executed — and in this project a surviving
mutation is read as an invariant nothing watches, which is the signal the
whole method exists to produce. More than eighty mutations have been applied
here since 2026-08-21, and this is the first evidence that any of them could
have lied.

`Dockerfile` has set `PYTHONDONTWRITEBYTECODE=1` since the image existed.
`bin/aistack_env.sh`, which ADR-0001 designates as the single source of truth
for the execution environment, did not. A developer and an image ran Python
two different ways, and ENG-TEST-0002 is C3 and asks for *portability across
environments*.
**Resolved 2026-08-27.** The declared environment exports it, and two tests
compare the declaration with what the image ships — the same shape as the
comparison between `requires-python` and the images' base.

*It does not restore confidence in the mutations already applied.* Nothing
recorded which ones ran against a warm cache, and re-running eighty
mutations to find out would cost more than it could return. What is recorded
is that the method had this hole until 2026-08-27, so that a reader weighing
an old "the mutation was killed" knows what it rested on.
**Derivable** yes, and now derived
**Qualification** none required; an interpreter running yesterday's code is
not a judgement call.

*Misfiled on its first writing, under `Risks`, and reported by
`register-coherence` before the commit — both of its rules at once, a
resolved entry among open ones and a section holding two natures. The check
was three hours old.*

#### GOV-0002/OS-030 — The register states each entry's condition twice

**Nature** `defect` · **Opened** 2026-08-27 · **State** resolved 2026-08-27 by `register-coherence`
**Observed** An entry declares its condition in its `**State**` field, and
again by the section it sits in. Two statements of one fact, and they drifted
twice in two days:

- **2026-08-23** — OS-023 and OS-024 were filed under *Defects* while
  declaring `non-conforming`, beside the two real defects of
  `sync_mirrors.sh`. Corrected in the same patch that closed OS-009 and
  OS-010, by an agent who happened to look;
- **2026-08-27** — OS-029 was filed under *Resolved* while declaring
  `State open`. An entry announcing itself as open, inside the section for
  closed ones, in the artifact whose entire purpose is to state what is open.

Both were found by reading. Neither was found by anything that runs.
**Resolved 2026-08-27.** `register-coherence`, the twelfth check, on two
rules:

- **a state and its section agree.** `resolved` belongs under *Resolved* and
  nothing else does. `partially mitigated` — OS-012's state — is not
  resolved, and a check treating any non-`open` word as closed would have
  moved it;
- **the open sections are homogeneous.** Every open entry in a section
  declares the nature of its neighbours.

**The second rule deliberately does not map natures to section names.** That
mapping lives in this register's prose, and a copy of it inside the check
would be one more pair of projections to drift apart — which is the defect
STD-0100 names for the classification vocabulary, and which this entry is an
instance of. Homogeneity catches the same misfiling without restating
anything.

*A limit of the second rule, observed 2026-08-27 while filing OS-035: a
`contract-debt` entry placed alone in `Risks` passes homogeneity, because a
section holding one nature is homogeneous by definition. The check compares
neighbours and cannot map a nature to a section name — deliberately, since
that mapping lives in this register's prose. A misfiled entry that is the
only one in its section is invisible to it, and a human found this one.*

Ten mutations were applied. The tenth survived the first pass: removing the
reset of the current entry at a section heading produced no failure, because
no test had an entry declaring no fields. It causes a *false* incoherence —
an unfinished entry adopts a state read from prose in the next section — and
that is now the case that holds it.
**Derivable** yes, and now derived
**Qualification** none required; a register that contradicts itself is not a
judgement call.

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
