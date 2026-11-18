---
artifact:
  id: GOV-0002
  title: Open State Register
  type: Governance Register
  semantic_type: Knowledge Artifact
  domain: Governance
  criticality: C2
  confidence: Declared
  version: 2.37
  status: Draft
  owner: Foundation
  created: 2026-08-22
  updated: 2026-11-18

relations:
  references:
    - FDN-0011
    - GOV-0001
    - STD-0100
---

# GOV-0002 — Open State Register

## Provenance of version 2.0

This register left `main` on 2026-10-10 with the rest of the heritage
(`94f7c15`) and returns on 2026-11-15, by decision of the owner, as a short
register: its rules are unchanged, word for word, and its history is not
copied. Version 1.123, with the 84 entries `OS-001` to `OS-084`, all resolved,
is at the tag `archive/heritage-2.0.0-rc1` under this same path. Entries opened
from 2026-11-15 continue the numbering at `OS-085`.

Between those two dates nothing recorded what AIStack knew about itself and had
not resolved. The entries below are what was measured on the day the register
returned; they are not a reconstruction of those five weeks.

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
Six natures are declared, and the table below is the declaration:

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

None open.

---

# Non-conforming instances

#### GOV-0002/OS-095 — Seven files of the validation suite stay at the tag

**Nature** `non-conforming` · **Opened** 2026-11-18 · **State** open
**Observed** the tag `archive/heritage-2.0.0-rc1` holds eight files under
`tests/integration/validation/`; `main` holds one
(`test_std_0300_scenario_2.py`, lot 8.6b). Run on `main` as they are, six tests of
the other seven fail, and none is a defect found: floors measured in August (65
artifacts, 19 types, 39 declarations, 29 register entries) that `main` does not
reach; twelve references to documents declared kept at the tag; dates of forty
documents read against a git history that starts on 2026-11-15.
**Derivable** yes
**Qualification** decided by the owner, 2026-11-18: they stay at the tag for the
2.1 release. After it, each file is re-measured (floors, references, dates) and
returns or is declared kept; no number is changed quietly.

OS-088 is in *Resolved*.

---

# Defects

#### GOV-0002/OS-096 — The Context Bundle names the host it was generated on

**Nature** `defect` · **Opened** 2026-11-18 · **State** open
**Observed** the `source` of each of the 64 artifacts of the bundle generated on
2026-11-18 is the absolute path of the directory it was generated in
(`ArtifactBuilder` sets `source=str(discovery.path)`). A bundle read elsewhere
names a machine and a user. No secret is involved, and `source` is not part of
the `content_hash`; about ten integrity checks read it, among them
`transport_residue`, which tests `location in artifact.source`.
**Derivable** yes
**Qualification** decided by the owner, 2026-11-18: not before the 2.1 release.
After it, `source` becomes relative to the repository root, with the checks that
read it re-read and tested.

OS-089 and OS-094 are in *Resolved*.

---

# Published artifacts

None open.

---

# Risks

None open.

---

# Decisions

None open. OS-091 is in *Resolved*.

---

# Resolved

An entry moves here with the date and what discharged it, and is never
deleted. A register that erased what it had closed could not show that a
rule ever bound anything.

`OS-001` to `OS-084` were resolved between 2026-08-22 and 2026-10-03. Their
entries are in version 1.123 of this register, at the tag
`archive/heritage-2.0.0-rc1`.

#### GOV-0002/OS-085 — The Kernel names what is outside it, a technology included

**Nature** `non-conforming` · **Opened** 2026-11-15 · **State** resolved 2026-11-15 by lot 3 of the GHE reintegration
**Observed** `python scripts/ghe_audit.py`, measure *The Kernel names something
that is not a generic mechanism*: six imports on `76649da` —
`aistack.providers.docker`, `aistack.providers.compose`,
`aistack.generators.docker` and three catalog views. `ARC-P-001`,
`ARC-P-004`. *First measured as ten imports, of which three named a
technology: seven named a generic mechanism, admitted since by `ADR-0027`
§ 7, and three were hidden by an exemption the audit gave the bootstrap.*
**Derivable** yes
**Qualification** conformed. The Kernel bootstraps from
`registrations.yml` (`ADR-0027` § 8), the task `docker.discover` is declared
in `aistack.tasks`, and the measure reads none. One technology was in the
Kernel by name and not by import, so the measure never saw it:
`SyncthingDefinition`, in `kernel/application`. It left with
`ApplicationDefinition` for `aistack.application` in the same lot.
**What the measure does not cover**: a technology named in the Kernel
without an import. On the day of the closure, `git grep -il
"docker\|syncthing" -- src/aistack/kernel` returned nothing, and *compose*
occurred there three times, as the English verb. Nothing re-runs that
search.

#### GOV-0002/OS-093 — The health cockpit exists in three copies

**Nature** `non-conforming` · **Opened** 2026-11-16 · **State** resolved 2026-11-16 by commit 5.2 and the MSI comparison
**Observed** by comparing, function by function, the cockpit of
`aistack/cli/health_render.py`, of `aistack/cli/console_render.py` and of
`aistack/troubleshooting/findings.py`. The copy in `console_render` differs
from `health_render` by its docstrings only; the one in `findings` differs
besides by where it reads its sources (`SOURCES.x` instead of the
`DEFAULT_X` constants). `technical_debt_score` exists in two copies.
Three places say what the health of the homelab is, and none is the
reference. `FDN-P-005`.
**Derivable** yes
**Qualification** to conform, in lot 5 (commit 5.2): the domains and
`build_cockpit` live in `aistack.health.domains`, parametrised by their
sources, and the three copies disappear. Decided by the owner, 2026-11-15,
at the closing of lot 4.
*Commit 5.2, 2026-11-16: done in the code. The nine functions were compared
after removing docstrings and renaming the paths: identical in the three
copies. `HealthSources` declares every path once (the assistant's copy read
its network observation from the working directory, then the checkout; that
resolution is now everyone's). `technical_debt_score` moved to
`aistack.health.technical_debt`. The two commands boot the Kernel and hand
its providers to the cockpit. Ten tests are gone, all of them guards against
the copies drifting apart.*
*MSI, 2026-11-16: `releve-cockpit.sh` read the three cockpits, both scores
and the assistant's list on the host AIStack runs on, from the repository
and outside the container, before (`14180b5`) and after (`7b0f119`): identical.
Not compared: the CPU consumption findings, an instantaneous measure that
differed between the two readings (filebrowser, firefly before;
aistack-docker-digest, aistack-docker-packages after) and is not part of the
cockpit. The web application, on the 2.0.0 image, is not verified.*

#### GOV-0002/OS-089 — Two architecture guards pass on nothing

**Nature** `defect` · **Opened** 2026-11-15 · **State** resolved 2026-11-17 by commit 5.3
**Observed** `tests/unit/kernel/test_architecture_boundaries.py`:
`test_runtime_does_not_depend_on_task_registry` iterated over
`src/aistack/kernel/runtime`, which did not exist;
`test_every_kernel_runtime_boot_call_in_cli_declares_a_trace_repository`
searched for `KernelRuntime.boot(`, which occurred nowhere under `src`. Both
passed vacuously from `19e73a6`.
**Derivable** yes
**Qualification** kept as they were until lot 5 rebuilt the execution path —
owner, 2026-11-15.
*Commit 5.3, 2026-11-17: the Runtime is back (four files under
`kernel/runtime`) and `aistack.cli.health_render` boots it with a
`FileTraceRepository`. Both guards read something. A third test fails if
either goes back to reading nothing.*

#### GOV-0002/OS-090 — VS-3 no longer explains why an item is included or excluded

**Nature** `non-conforming` · **Opened** 2026-11-15 · **State** resolved 2026-11-17 by commit 5.9
**Observed** `STD-0300` criterion 3.2 was satisfied on 2026-09-04 by
`src/aistack/selection/explanation.py` and
`tests/unit/selection/test_selection_explanation.py`. Neither is in `main`
on `e574fb7`; `git grep explain_selection -- src` returns nothing. The
selection itself still runs.
**Derivable** yes
**Qualification** decided by the owner, 2026-11-15: the explanation returns
from the tag when the selection screen displays it, in lot 5 (`ADR-0027`).
Until then 3.2 stays *not verifiable in `main`*. It is not restored before
something calls it.
*Commit 5.9, 2026-11-17: `aistack.selection.explanation` and its seven tests come back from the tag, and the selection screen (`aistack.sync.screen.page_context`, template `selection/index.html`) names on each line, in the language of the page, the rule that decided the item: ticked, redundant, inherited, excluded. `STD-0300` still reads 3.2 as not verifiable in `main`; it is brought up to date with the re-run of lot 5.11, as the standard's own requalification.*

#### GOV-0002/OS-086 — Entry points run without the Kernel, and the one registered Task is never executed

**Nature** `non-conforming` · **Opened** 2026-11-15 · **State** resolved 2026-11-17 by commit 5.12
**Observed** `python scripts/ghe_audit.py`: 22 of the 25 entry points import
nothing from `aistack.kernel`; no module outside the Kernel imports its
execution, resolution or tasks packages. `kernel/runtime` was removed on
2026-10-10 (`19e73a6`). `ARC-P-002`.
*Lot 4, 2026-11-15: ten files of application code build a provider
themselves, 23 pairs of a file and a provider (`ADR-0027` § 9). The health,
console and troubleshooting chains and the priority screen ask the Kernel for
theirs since that day: 19 of 25 entry points, 7 pairs. The 7 are the
providers configured at each use, which stay with their caller by decision
and stay reported. Building the Kernel to ask it for a provider is not yet
running through it: no Task is executed. Lot 4 is complete; what is left of
this entry is lot 5.*
*Commit 5.3, 2026-11-17: `kernel/runtime` returns from the tag (four files,
reduced to resolve, execute, trace, keep the trace) and the health chain is
the first Task it executes, `health.render`. `docker.discover` leaves
`registrations.yml`. The measure *A registered Task is never executed* reads
none; 19 of 25 entry points still do not build the Kernel (the health
command already did). The chains left are 5.4 to 5.7.*
*Commit 5.4, 2026-11-17: the architecture chain is the second Task the
Runtime executes, `architecture.render`. The two providers it configures at
use (Beszel, HTTP probes) are built in the Task and not in the command: two
entries of the baseline are renamed, seven pairs still (`ADR-0027` § 4).
The chains left are 5.5 to 5.7.*
*Commit 5.5, 2026-11-17: the console chain is the third Task the Runtime
executes, `console.render`. The console command already asked the Kernel for
its providers, so 19 of 25 entry points still do not build it, and seven
pairs remain. The chains left are 5.6 and 5.7.*
*Commit 5.6, 2026-11-17: the Time Machine chain is the fourth Task the Runtime
executes, `timemachine.rebuild`. Its command did not build the Kernel: 18 of 25
entry points now do not. Its trace is written in the data directory the
command is given, beside the streams the graph is rebuilt from. The chains left
are `network_docker_discover`, `hosts` and `data_budget`, one by one (5.7).*
*Commit 5.7a, 2026-11-17: `network_docker_discover` is the fifth Task the
Runtime executes, `network_docker.discover`. 17 of 25 entry points do not build
the Kernel. Its provider, configured at use, is built in the Task, as at 5.4:
the baseline entry is renamed, seven pairs still. The SSH key path is read from
the environment by the Task, never carried by the request. Left: `hosts` and
`data_budget`.*
*Decision 5.7, 2026-11-17: `hosts`, a read-only status command like
`healthcheck`, is declared exempt (`ADR-0027` § 10); it stays in the audit's
list of entry points that do not build the Kernel, as the other exempt
commands do. Left: `data_budget`.*
*Decision 5.7b, 2026-11-17: `data_budget`, a measure and a compression action
that produce no artifact, is declared exempt too (`ADR-0027` § 10). Lot 5.7 is
closed: 17 of 25 entry points do not build the Kernel, of which the permanent
monitors and the exempt commands are declared; what is left of this entry is
5.8 to 5.10.*
*Commit 5.10, 2026-11-17: the audit reads *A registered Task is never executed*
Task by Task and measures a new departure, *An entry point builds the Kernel
and never executes through the Runtime*: `ai_reason`, `dock` and the web
application (3). Each is to be decided by the owner: converted, or declared
exempt like the commands above.*
*Commit 5.10b, 2026-11-17, decisions of the owner: `ai_reason` becomes the sixth
Task the Runtime executes, `ai.reason`; `dock` is declared exempt (an action
command through the Kernel's transaction); the web application is a declared
exception until a screen executes a Task (`ADR-0027` § 10). The new measure
reads 2: `dock` and the web application.*
*Commit 5.8, 2026-11-17: the web application reads Docker (priority screen)
and the assistant's findings through the providers of its own Kernel, not one
booted per call (`ADR-0027` § 9). It runs no Task, so no trace per view. The
2.0.0 image does not carry it until the next one is published.*
**Derivable** yes
**Qualification** to conform, in lot 5. Discharged: the chains that produce an
artifact run through the Runtime as Tasks with a durable trace (six); what does
not is declared in `ADR-0027` § 10 and measured by `scripts/ghe_audit.py`, which
can only get shorter. *Commit 5.12, 2026-11-17: the architecture documents of
the Kernel and its concepts (`ARCH-0002`, `ARCH-0007`, `ARCH-0010`,
`ARCH-0012`) return from the tag, revised against `main`; the entry closes.*

#### GOV-0002/OS-088 — `main` cites documents it does not hold

**Nature** `non-conforming` · **Opened** 2026-11-15 · **State** resolved 2026-11-18 by commit 8.7
**Observed** `python scripts/ghe_audit.py`, measure *A document is cited and is
not in the tree*; the list is `tests/reference/ghe_audit_baseline.json`.
`FDN-P-005`.
**Derivable** yes
**Qualification** decided by the owner, 2026-11-15: the core returns
(`ADR-0027` § 1); what stays at the tag is declared in `FDN-0001` § *Kept at
the tag* and is no longer reported; the architecture documents return with
the lot that brings their code back. What remains reported is those, and
`OS-092`.
*Commit 5.12, 2026-11-17: `ARCH-0002`, `ARCH-0007`, `ARCH-0010` and `ARCH-0012`
return, revised; 8 cited and absent, then 4. `ADR-0005` to `ADR-0007` and
`ARCH-0013` stay reported until lot 8 (`ADR-0027` § 5).*
*Commit 8.5, 2026-11-18: `ADR-0005`, `ADR-0006` and `ARCH-0013` return, revised;
`ADR-0007` (the transfer) stays at the tag and is declared in `FDN-0001` § *Kept
at the tag*. 4 cited and absent, then 0. The entry closes with lot 8.7.*
*Commit 8.7, 2026-11-18, closure: `python scripts/ghe_audit.py` reads 0 for *A
document is cited, is not in the tree and is not declared kept at the tag*, and
`tests/reference/ghe_audit_baseline.json` holds `"documents_cited_and_absent": []`:
the suite fails the day a document is cited and neither in the tree nor declared
at the tag. The measurement is inside the repository, the suite is it. What
carried the condition and is left as history: `ADR-0027` § 5 and § 13 (the
documents that returned with their code, and the one that did not). The
documents declared at the tag are listed in `FDN-0001` § *Kept at the tag*;
`OS-092` is a separate entry.*

#### GOV-0002/OS-091 — Nine criteria of STD-0300 have not been executed on 2.0.0

**Nature** `decision` · **Opened** 2026-11-15 · **State** resolved 2026-11-15 by the owner's decision
**Observed** `STD-0300` § *Requalification against 2.0.0*: 1.1 to 1.4, 4.2,
4.4, 4.5, 4.8 and 4.9 were verified on GIGABYTE between 2026-08-22 and
2026-09-11, with `aistack.cli.docker_catalog` and
`aistack.cli.runtime_diagnose`. Neither command is in `main`, and AIStack now
runs on another host.
**Derivable** no
**Qualification** decided: each is re-run on the host AIStack runs on, in
lot 5, through the entry point its chain gains when it runs through the
Kernel. No throwaway command is rebuilt for it. Until then `STD-0300` reads
them *satisfied before 2.0.0, not re-run*, and none is withdrawn.
**Executed** 2026-11-17 on the MSI (`STD-0300` 1.29, § *Re-run on 2.0.0*): 4.4,
4.5 and 4.9 re-run live through `ai.reason`; 1.1 to 1.4, 4.2 and 4.8 have no
chain to re-run through and keep *satisfied before 2.0.0, not re-run*, the
reason written. No criterion is withdrawn.

#### GOV-0002/OS-092 — Two identifiers are cited and were never documents

**Nature** `non-conforming` · **Opened** 2026-11-15 · **State** resolved 2026-11-15 — both became documents
**Observed** `python scripts/ghe_audit.py`, measure *A document is cited, is
not in the tree and is not declared kept at the tag*. `OPS-0009` is cited by
`OPS-0004` and by the release notes as the document that governs
`pra_tests.yml`; `QUAL-0001` is cited by `ADR-0010` and `ADR-0011`. Neither is
under `docs/` in `main`, and neither is under `docs/` at
`archive/heritage-2.0.0-rc1`. `ADR-0011` names
`claude/QUAL-0001-GOVERNED-LLM-EXPERIMENTS-HANDOVER.md`, a session note.
**Derivable** yes
**Qualification** decided by the owner, 2026-11-15: both are written.
`OPS-0009 — Restore Test Freshness` describes what `main` does and decides
nothing new; `QUAL-0001` summarises the session note under
`docs/06-reference/`, and `STD-0102` gains the `QUAL-` prefix.

#### GOV-0002/OS-087 — The disk is written outside a transaction

**Nature** `non-conforming` · **Opened** 2026-11-15 · **State** resolved 2026-11-17 by lot 6 (commits 6.1 to 6.6)
**Observed** `python scripts/ghe_audit.py`: 35 files outside
`src/aistack/transaction` write, move or delete on disk. `GOV-P-002`,
`ARC-P-012`.
*Commit 5.3, 2026-11-17: 34. `aistack.cli.health_render` no longer writes:
the plan page goes through `write_view`, in the module that already writes
the other generated artifacts.*
*Commit 5.5, 2026-11-17: 33. `aistack.cli.console_render` no longer writes: the
links in the public directory and its index go through `ensure_link` and
`write_view`, in the same module.*
**Derivable** yes for the list; no for telling a generated artifact
(`ENG-P-003`) from a modification of knowledge — that is a reading.
**Qualification** unknown until that reading is done, in lot 6.
*Commit 6.1, 2026-11-17: the reading is done, file by file
(`claude/INVENTAIRE-2026-11-17-ecritures-lot-6.md`). Decided by the owner
(`ADR-0027` § 11): seven writes go through a transaction (the declarations a
person changes from a screen, and the materialisation of a selection), one is
deleted (`generators/filesystem/copy`, dead code), and 25 are declared exempt
(the state a service keeps for itself, the process locks, the installation,
the maintenance, the recognised writer of generated artifacts, and the API
keys: no secret in a payload or a trace). Left: 6.2 to 6.6.*
*Commit 6.2, 2026-11-17: 32. The operation `declaration.write` exists
(`ADR-0027` § 11); the SSH user names of the network discovery screen go
through it. Left: the priority and selection stores, `sync/screen`,
`arrivals/declare`, `instance/data_location`, then 6.3 to 6.6.*
*Commit 6.2 (priorities), 2026-11-17: 31. The CPU priority screen and the
troubleshooting fix write through `declaration.write`. Left: the selection
store, `sync/screen`, `arrivals/declare`, `instance/data_location`, then 6.3
to 6.6.*
*Commit 6.2 (selection), 2026-11-17: 30. The sync screen records the selection
through `declaration.write`. Left: `arrivals/declare`, `instance/data_location`,
then 6.3 to 6.6.*
*Commit 6.2 (arrivals), 2026-11-17: 29. The container declared from the
arrivals goes through `declaration.write`. Left: `instance/data_location`,
then 6.3 to 6.6.*
*Commit 6.2 (data location, 6.2 closed), 2026-11-17: 28. Choosing the place of
the data, and forgetting the choice, go through `declaration.write`. Left: 6.3
to 6.6.*
*Commit 6.3, 2026-11-17: 27. The hard links of a device's folder go through
`selection.materialise`; `generators/filesystem/hardlink` no longer writes.
`cli/sync_apply` is exempt like `dock` (owner's decision). Left: 6.4 to 6.6.*
*Commit 6.4, 2026-11-17: 26. `generators/filesystem/copy` (dead code) is
deleted. Left: 6.5 and 6.6.*
*Commit 6.5, 2026-11-17: nothing is left to do. The audit lists apart the 26
files declared exempt (`ADR-0027` § 11) and the measure of this item is empty.
Left: 6.6, the closing and the check in a container.*
*Commit 6.5, 2026-11-17: nothing is left to do. The audit lists apart the 26
files declared exempt (`ADR-0027` § 11) and the measure of this item is empty.*
*Commit 6.6, 2026-11-17: closed. Measured inside the repository:
`python scripts/ghe_audit.py` reports 0 writes outside a transaction and 26
declared exempt, and the suite fails on a write in a file that is not declared
(`tests/unit/scripts/test_ghe_audit.py`). Measured on the host (the MSI, at
`4073820`, 2026-11-17): `./run_sync.sh --dry-run` then
`./run_sync.sh music--phone` through `selection.materialise` give the same
report, `+7 ~0 -7 =6577`, no failure, nothing left in the checkout; the
last-application record is rewritten. The same `+7 -7` is in the record of
2026-10-12, before lot 6: it is `OS-094`, not a regression. What still said
the condition and was read: the table of `ADR-0027` § 5, § 11 (“until then the
files stay in the baseline”, brought up to date) and this register; nothing
else names the item.*

#### GOV-0002/OS-094 — The sync links a file under a name Syncthing renames, and does it again at every pass

**Nature** `defect` · **Opened** 2026-11-17 · **State** resolved 2026-11-17 by commit 6.7
**Observed** on the MSI, 2026-11-17: `./run_sync.sh music--phone` reports `+7 -7`
at every pass, as it did on 2026-10-12 (`reports/generated/sync/applied/`).
`/media/TechData/Storage/Music/Asa/Beautiful Imperfection/05. Bimpé.mp3` is
named in NFD (“e” and a combining accent); in `Music-Android` the same file is
named in NFC. Seven files of the library are named in NFD. The destination
folder is Syncthing's, which corrects the normalisation of names by default:
it renames what AIStack linked, the next pass does not find the name it wants,
links it again and removes the NFC one as not designated.
**Derivable** yes (`diag_sync_names.py` lists the seven; a test with a name in
NFD reproduces it)
**Qualification** decided by the owner, 2026-11-17: the target name is the NFC
form of the source's name, and names are compared in NFC, so that an
unchanged selection writes nothing. The phone already has the seven files
under the NFC name: nothing is lost.
*Commit 6.7, 2026-11-17: `generators/filesystem/hardlink._desired` keys the
target in NFC; two tests (a library in NFD: linked in NFC then unchanged on the
second pass; an NFD name left in the target: replaced). Open until measured on
the MSI: the condition is about a host (the second pass of
`./run_sync.sh music--phone` must report `+0 ~0 -0`).*
*Closed 2026-11-17. Measured on the MSI at `f1f8041`, 21:26:
`./run_sync.sh --dry-run`, then `./run_sync.sh music--phone` twice, all report
`+0 ~0 -0 =6584` (before: `+7 ~0 -7 =6577`); the checkout is clean. What still
said the condition: `ADR-0027` § 11 (commit 6.6) and the open point of that
ADR, brought up to date; nothing else names the item.*
