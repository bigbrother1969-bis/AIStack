---
artifact:
  id: ADR-0027
  title: GHE Reintegration
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.25
  status: Accepted
  owner: Architecture
  created: 2026-11-15
  updated: 2026-11-17

relations:
  references:
    - FDN-0001
    - FDN-0003
    - FDN-0004
    - FDN-0012
    - GOV-0002
    - STD-0300
    - ADR-0004
    - ADR-0016
    - ADR-0019
---

# ADR-0027 — GHE Reintegration

## Status

Accepted, 2026-11-15, by the owner, the day of the proposal
(`ADR-0016` § 3). Each decision below was taken by the owner that day, one
by one, as the measures that motivate it were produced.

## Context

From 1.2 to 2.0 the roadmaps were driven by features. On 2026-10-10 the
release candidate of 2.0.0 removed from `main` what nothing ran
(`19e73a6`, 382 files) and kept only the documents that describe the
product (`94f7c15`, 122 files). The heritage is whole at the tag
`archive/heritage-2.0.0-rc1`.

Two things left with it that the product still depended on:

- **the principles.** The code cites them by identifier — `ARC-P-006` 46
  times, `GOV-P-001` 23 times — and the registry that defines them was no
  longer beside it. Nor were the Constitution, the Glossary and the
  Manifesto. A session working in `main` could not read what it was asked
  to respect;
- **the validator.** `aistack.cli.knowledge_integrity` and its checks were
  the only thing that verified the heritage. Nothing replaced them.

Measured on 2026-11-15 by `scripts/ghe_audit.py`, written that day:

| Principles | Departure | Count |
|---|---|---|
| `ARC-P-001`, `ARC-P-004` | The Kernel names something outside itself | 10 imports — see § 7 |
| `ARC-P-002` | An entry point never builds the Kernel | 22 of 25 |
| `ARC-P-002` | The one registered Task is never executed | 1 |
| `GOV-P-002`, `ARC-P-012` | The disk is written outside a transaction | 35 files |
| `FDN-P-005` | A document is cited and is not in the tree | 22, once the first fifteen had returned |

The Kernel Runtime itself is at the tag: `kernel/runtime` no longer
exists, and the Task `docker.discover` is registered and reached by
nothing.

The Manifesto forbids the obvious answer. *Preserve working heritage.
Migrate incrementally. Do not rewrite functioning code because a cleaner
architecture exists.* 2.0.0 is in production and its suite is green.

## Decision

### 1. The core of the principles returns to `main`; the rest stays at the tag

Option B of three. Not everything (it would undo the decision of
2026-10-10 and bring back some 58 000 lines, much of it unexecuted), and
not a separate repository (two sources, and the principles still out of
sight where the work is done).

Returned on 2026-11-15: the Manifesto (amended, 1.1), `FDN-0001` to
`FDN-0004`, `FDN-0007` to `FDN-0012`, `ENG-TEST-0001`, `ENG-TEST-0002`,
`STD-0100`, `STD-0102`, `STD-0300` (requalified against 2.0.0),
`GOV-0002` (its rules, and a new history), `OPS-0001`, `OPS-0003` and
`ARCH-0009`.

### 2. Nothing returns without a use

A document returns when it is read or verified. A module returns in the
lot that executes it. Nothing is restored in bulk from the tag.

### 3. What stays at the tag is declared in one place

`FDN-0001` § *Kept at the tag* lists the documents that do not return. A
citation of one of them leads there. No citation is rewritten.

### 4. The departures are measured, and the list only gets shorter

`scripts/ghe_audit.py` reads `src/aistack` and the documents, and
reports every departure it can measure.
`tests/reference/ghe_audit_baseline.json` records them. The governed
suite fails on a departure that is not in the baseline, and on a baseline
entry that no longer exists.

It is a script and a test, not the nineteen checks of the validator: it
verifies what is cited, registered and imported, and nothing about the
content of a document.

**The baseline was extended twice on 2026-11-15**, by one entry each
time: a returning document (`FDN-0002`, then `STD-0300`) cited a
document that had not returned (`ARCH-0010`, then `STD-0200`). Both are
recorded in their commits. A returning document brings its citations
with it; that is the first case in which an entry is added.

**Second case, 2026-11-17 (commit 5.4).** A command that builds a provider
configured at each use becomes a Task: the entry follows its caller. It is
renamed, not added, and the count does not change. Decided by the owner
when `aistack.cli.architecture_render` became the Task
`architecture.render` (`BeszelProvider` and `HttpProbeProvider` now built
in `aistack/tasks/architecture_render.py`).

### 5. The code is brought back within the principles in lots

Each lot is a series of atomic, reversible commits, validated on the
production of 2.0.0 — the suite green, the Cockpit unchanged, the
generated artifacts compared before and after. The owner decides at the
end of each lot.

| Lot | Subject | Closes |
|---|---|---|
| 3 | No technology in the Kernel | `GOV-0002/OS-085` |
| 4 | Application code asks the Kernel for a provider (§ 9) | part of `OS-086` |
| 5 | The chains run through the Kernel, one at a time: health, architecture, console, Time Machine | `OS-086`, `OS-089` |
| 6 | Modifications of knowledge go through a transaction | `OS-087` |
| 7 | The declarations edited by hand on the host become governed knowledge | — |
| 8 | Self-onboarding: host executors, Context Bundle, boot report | VS-2 of `STD-0300` |

The architecture documents of the Kernel and of its concepts
(`docs/01-architecture/kernel/` and `docs/01-architecture/concepts/` at
the tag) return revised with lots 3 to 5, and `ADR-0005` to `ADR-0007`
and `ARCH-0013` with lot 8: they describe code
that is at the tag, and return when the code they describe does.

**Returned on 2026-11-17 (5.12):** `ARCH-0002`, `ARCH-0007`, `ARCH-0010` and
`ARCH-0012`, revised against `main`: each says what the code holds, with its
provenance. `ARCH-0002` and `ARCH-0007` are rewritten (components, extension
points and registries as they are today); `ARCH-0010` and `ARCH-0012` keep
their principles and gain a dated status. No returning document cites one that
is still at the tag: the baseline of cited and absent documents falls from 8
to 4 and gains nothing.

### 6. No abstraction without a present case

`ARC-P-006`. A lot moves what exists behind the Kernel. It builds nothing
the product does not already do.

### 7. The Kernel may name a generic mechanism, never a technology

Decided by the owner, 2026-11-15, at the opening of lot 3. The audit of
that morning counted every import of the Kernel that left the Kernel: ten.
Seven of them named no technology — the transport, the transaction
(`ADR-0019` § 6 places it in `KernelServices`) and the history. The Generic
Kernel Principle (`FDN-0004`) forbids technologies in the Kernel; it does
not forbid the Kernel a mechanism that carries none.

The admitted mechanisms are declared in one place, `GENERIC` in
`scripts/ghe_audit.py`: `aistack.transport`, `aistack.transaction`,
`aistack.history` and `aistack.generators.history`. They are not moved
into the Kernel: that would rename dozens of files for no change of
behaviour.

The same reading removed an exemption. The audit let the bootstrap of the
Kernel name anything but a provider or a generator, and so did not see it
import three catalog views — Docker, music, media. The bootstrap is now
held to the rule of the rest of the Kernel. **Measured the same day: 6
imports name a technology**, where the first count read 10 of which 3 did.

### 8. The Kernel bootstraps from declared registrations

Decided the same day. *"The Kernel shall bootstrap itself from governed
registrations rather than explicit technology-specific wiring"*
(`FDN-0004`, Kernel Bootstrap Principle). The registrations are declared
in a file outside the Kernel; the Kernel reads it and registers what it
names. `create_kernel()` stays the one call an application makes.

What this costs is said here once: a registration that names a class
that does not exist fails when the Kernel boots, where an import failed
when the module was read, and `mypy` no longer sees it. A test of the
governed suite checks every declared path against its contract.

### 9. Application code asks the Kernel for a provider

Decided by the owner, 2026-11-15, at the opening of lot 4. `FDN-0004`
validated the Kernel Bootstrap Principle on one sentence: *"DockerProvider
is no longer instantiated directly by application code."* Measured that
day by `scripts/ghe_audit.py`: twelve providers exist, two are registered,
and ten files of application code build one — 23 pairs of a file and a
provider it builds. `DockerProvider`, which is registered, is built by
five of those files.

**Scope.** The six providers built with no argument come from the
registry: `docker`, `compose`, `storage`, `backup`, `gpu`, `host`. The six
built from a configuration at each use — Beszel, the HTTP probe, Jellyfin,
the media library, the network discovery, Syncthing — stay built by their
caller, and stay reported by the audit: 7 of the 23 pairs. Registering them needs a way for
the Kernel to hand each its address, token or path; no case asks for that
mechanism yet (`ARC-P-006`).

**Order.** One chain at a time, health first. A provider is registered in
the commit in which its callers start asking the registry for it: a
provider registered and asked for by nothing would be the defect of the
Task nothing executes.

**Contract.** The registry was typed on `KnowledgeProvider`, whose one
method is `collect()`. The providers of storage, backup, GPU and host have
none: they expose specialised readings. All twelve carry the identity of
the base contract `Provider`, which *"does not prescribe how information
is obtained"*. The registry is typed on `Provider`. `KnowledgeProvider`
stays the contract of those that `collect()`, and a Task built on a
provider still requires it, checked when the Kernel boots. No provider is
rewritten.

The plan of that morning named lot 4 *capabilities registered at
bootstrap; services exposed*. Read against the code: the transaction
service is already in `KernelServices` (`ADR-0019` § 6), and the Capability
Model (`ARCH-0012`, Draft, at the tag) has open points no case settles.
Lot 4 is the providers.

**The web application** (5.8, 2026-11-17) boots one Kernel when it starts
(`app.state.kernel`) and reads through its providers: the screens that read
Docker (the priority screen's discovery) and the assistant's findings take
that registry, where each call used to boot a Kernel of its own. A
collaborator injected into `create_app` still replaces the default, as the
tests do. The web application executes no Task: no trace is written by a
page view, and the volume of traces stays an open point until one does.

**Criterion 3.2 gets its explanation back** (5.9, 2026-11-17), as the owner
decided on 2026-11-15: `aistack.selection.explanation` returns from the tag
with its test, because the selection screen now displays it. Every item of
the catalog, included or excluded, shows on its line the rule that decided
it, in the language of the page. The tag's module is kept as it was; it gains
two fields, `kind` and `by`, so that the screen translates the rule from data
and parses no sentence.

**What the audit measures of the chains** (5.10, 2026-11-17). Two measures
are added to the one that existed. *A registered Task is never executed* is
now read Task by Task, from `registrations.yml`: one Task nobody executes no
longer hides behind another that is. *An entry point builds the Kernel and
never executes through the Runtime* names the commands that take their
providers from the Kernel and run a chain it does not trace: `ai_reason`,
`dock` and the web application at the time of the measure. They are put to
the owner one at a time; until decided they are the baseline of the new
measure, which like the others can only get shorter. Decided on 2026-11-17:

- `ai_reason` becomes a Task, `ai.reason` (5.10b): a chain that produces
  knowledge, the AI reasoning read by the Time Machine, run on demand. Its
  engine is configured at use and is built by the Task. The command prints
  what the Observation carries.
- `dock` is exempt: an action command, which changes the host through the
  Kernel's transaction (§ 6 of `ADR-0019`), started every two minutes by its
  timer; a trace of each pass would say nothing more than the transaction
  does. It joins the exempt commands and stays in the baseline of the new
  measure.
- The web application is a declared exception: it reads and serves, and
  executes no chain. It stays in the baseline of the new measure until a
  screen executes a Task, which is when the volume of traces is decided.

### 10. Chains run through the Kernel as Tasks

Decided by the owner, 2026-11-16, at the opening of lot 5. A chain passes
through the Kernel when it is a Task declared in `registrations.yml`,
executed by the Runtime from a Request, and a trace of it is kept; the
command or the page becomes a caller. There is no *chain* type to rebuild:
the decision of 2026-08-28, kept at the tag, is that a pipeline is a named
sequence, not an object.

**Which entry points.** Three families, among the 19 that do not build the
Kernel:

- *Chains run once that produce an artifact of knowledge* — they become
  Tasks. Four: `timemachine_rebuild`, `network_docker_discover`, `hosts`,
  `data_budget`; with the health, console and architecture chains, which
  already build the Kernel. Health, architecture, console and Time
  Machine are converted first (commits 5.3 to 5.6); the other three are
  decided one at a time (5.7). `network_docker_discover` is converted
  (5.7a). `hosts` is not: the owner decided on 2026-11-17 that it is a
  status command, read only, like `healthcheck`, and joins the exempt
  commands below; a trace at every consultation would add nothing and grow
  the history. `data_budget` is not converted either (5.7b, decided on
2026-11-17): it prints a measure of the disk budget and, with `--compress`,
compresses old observations, an action. It produces no artifact, and the
vigil compresses daily by its own way. It joins the exempt commands below.
Lot 5.7 is closed.
- *Permanent monitors* — the four `docker_*_monitor`,
  `resource_priority_monitor`, `vigil` and `restart_watch`. A Task runs a
  Request and returns an Observation; a daemon that listens without end is
  not in that contract. Out of lot 5, declared as a known exception.
  `vigil` and `restart_watch` were first counted among the chains; both
  loop without end.
- *Administration and action commands* — `config_init`, `setup_token`,
  `web_admin_password`, `explications_admin`, `healthcheck`, `hosts`, `data_budget`, `dock`, `sandbox`,
  `pra_schedule`, `sync_apply`. Not chains of knowledge: exempt, listed in
  one place (the audit) and recorded here.

**The Runtime** comes back from the tag, reduced to what the lot executes —
resolve, execute, trace, keep the trace (`ARC-P-006`; a module returns when
it is executed). It is not rewritten.

**The Task `docker.discover`** was registered, executed by nothing, and the
artifact it wrote was read by nothing. It left `registrations.yml` in the
commit in which the first Task really executed replaced it as the case of
validation (5.3, 2026-11-17). Its code stays in `aistack.tasks` until
decided.

**The first chain through the Runtime** is the health chain, the Task
`health.render` (5.3). It is built on the whole provider registry of its
Kernel: `registrations.yml` gains the key `all_providers: true`, for a Task
that reads several providers, beside `provider:`, which names one. The
command `aistack.cli.health_render` boots the Runtime, hands it one Request
and prints what the Observation carries.

**The second chain** is the architecture chain, the Task
`architecture.render` (5.4), built the same way: on the whole provider
registry, executed from `aistack.cli.architecture_render`. Its Beszel
credentials are read from the environment by the Task, never carried by the
request: the Runtime keeps the request, payload included, in its trace.

**The third chain** is the console chain, the Task `console.render` (5.5),
built the same way and executed from `aistack.cli.console_render`. The
symlinks of the public directory and its index page are written through
`ensure_link` and `write_view` of `aistack.generators.history`, so the command
and the Task add no writer to the baseline: the command's entry leaves it.

**The fourth chain** is the Time Machine chain, the Task `timemachine.rebuild`
(5.6). It reads no provider: what it rebuilds from is on disk, so it is
declared without `provider:` or `all_providers:`. The command takes the data
directory as an argument, so the trace is written there
(`<dir>/history/execution-trace/`), not in the working directory. A later
rebuild of the same directory reads that stream like any other: the graph
shows what the Runtime executed.

**The fifth chain** is the network discovery, the Task
`network_docker.discover` (5.7a). It is run on demand and by the vigil, never
by `architecture.render`: a scan with SSH attempts is an action. Its provider
is configured at use and follows its caller (§ 4), and the SSH key path is read
from the environment by the Task, as the Beszel credentials are: the request,
kept in the trace, carries none.

**The trace of a Task** — decided by the owner, 2026-11-17, as proposed:

- *Where.* `reports/generated/history/execution-trace/`, the latest in
  `reports/generated/execution-trace.json`: the stream `ADR-0011` already
  names, written by `FileTraceRepository` through the mechanism of every
  historised stream, read by the Time Machine and by
  `aistack.cli.history_query`. A command that boots the Runtime passes it
  explicitly; the Runtime's default stays in memory, so that no test writes
  into the repository.
- *How long.* Always, as every historised stream (`ADR-0011` § 11,
  decision of 2026-09-03): nothing is deleted. After 90 days the compaction
  of `ADR-0021` compresses it in place with the others.
- *Its place in the budget.* None of its own: the trace lives under
  `history/`, so the 2 GB of `ADR-0021` measure it and the compaction
  covers it. `tests/unit/data_budget/test_traces_are_compacted.py` fails if
  a trace is kept somewhere the compaction does not reach.
- *To watch.* The volume follows how often a chain runs. A command run by
  the vigil or by hand leaves one trace per run; a web page that ran a
  chain at each display would leave one per view. That is decided when the
  web application passes its own Kernel (5.8), after the volume has been
  measured on the host.

**One cockpit first.** The three copies of the health cockpit
(`GOV-0002/OS-093`) become one before any chain goes through the Runtime
(5.2): three copies are not sent through it.

### 11. The disk is written through a transaction when a person's knowledge or the host changes

`GOV-P-002`, `GOV-0002/OS-087`. Read on 2026-11-17 (lot 6, commit 6.1): the
33 files of `src/aistack` that write, move or delete on disk outside
`aistack.transaction`, one by one
(`claude/INVENTAIRE-2026-11-17-ecritures-lot-6.md`). The principle governs a
modification of knowledge, and an action on the host that a person's choice
triggers. It does not govern what a service keeps for itself.

**To go through a transaction** (the operations are built in 6.2 and 6.3;
each is registered by kind in `KernelServices.transactions`, as the dock's
nine are):

- the declarations a person changes from a screen: the CPU priorities
  (`priority/yaml/store`), the selection of a pair (`selection/yaml/store`,
  `sync/screen`), the SSH user names (`network_discovery/yaml/store`), the
  container declared from the arrivals (`arrivals/declare`) and the place
  chosen for the data (`instance/data_location`) — one kind of operation,
  `declaration.write`: whole-file atomic write, the copy kept before, the
  author and the reason in the trace;
- the materialisation of a selection into a device's folder
  (`generators/filesystem/hardlink`) — `selection.materialise`, which keeps
  its report.

**Declared exempt**, decided by the owner on 2026-11-17, because what they
write is not knowledge and no person's choice triggers it:

- *The state a service keeps for itself*: the checkpoints of the four
  monitors and the digest registry, the restart watch's attempts, journal and
  state, the notification state and the snapshot of the vigil, the host
  collector's state, the arrivals' last pass, the PRA scheduled-test journal,
  the dock's proposals (a change is already a transaction, `ADR-0019` § 6),
  the sandbox's run directory and the last materialisation report. Rewritten
  at every pass: one trace per write would grow the history and say nothing.
- *The process locks*: `dock/executor` and `cli/sync_apply` write a lock file.
- *The installation*: `config_init`, `instance/declarations`,
  `instance/first_start` and `instance/setup_wizard` copy the shipped
  declarations on the first start and keep their fingerprints and the
  assistant's token; several services start together, so each write is whole.
- *The maintenance*: the compression of `ADR-0021` (the compressed copy is
  verified before the original goes; its command is already exempt, § 10) and
  the purge of explanations, which is the development phase's one exception
  (`ADR-0016`) and goes with that phase.
- *The recognised writer of generated artifacts*, `generators/history`
  (`ENG-P-003`): the writer, not an exception.
- *The API keys* (`api_keys`): **no secret travels in a payload or in a
  trace.** A transaction carries its values in the request and the trace
  serializes the request, so the value of a key would be kept in the history.
  The write stays whole, in mode 0600.

**To delete**: `generators/filesystem/copy`, called by nothing in `src` or in
the tests (§ 2).

The audit separates what is declared exempt from what is left to do (6.5): the
baseline holds both lists and can only get shorter.

**Commit 6.4, 2026-11-17.** `generators/filesystem/copy` is deleted (it held
`generate_copy_folder`, destructive and untested, and `generate_symlink_folder`;
nothing in `src` or in the tests called either, and the definition of the
phone selection had already dropped the former on purpose). The maintenance
writes of § 11 (`data_budget/budget`, the purge of explanations) are exempt
and unchanged. Baseline 27 → 26.

**Commit 6.6, 2026-11-17: lot 6 closed.** `OS-087` is resolved, with its
measurement inside the repository (the audit, the suite) and on the host (the
MSI at `4073820`: a dry run and a real application of `music--phone` through
`selection.materialise`, same report, no failure, a clean checkout). The run
showed a defect that predates the lot (`+7 -7` at every pass since 2026-10-12:
Syncthing renames the NFD names the sync links): `OS-094`, left open.
`cli/sync_apply` had no timer on the MSI (`aistack-sync.timer` is installed
with the content disks); the check was run by hand.

**Commit 6.5, 2026-11-17.** The audit separates what is declared exempt from
what is left to do. `scripts/ghe_audit.py` holds the list of exempt files with
the reason of each (`EXEMPT_WRITES`, the categories above); the measure
`disk_writes_outside_a_transaction` is what remains and is empty, and the new
measure `disk_writes_declared_exempt` lists the 26 files that still write on
purpose. Both are held by the baseline: a write in a file that is not declared
fails the suite; so does an exemption whose file no longer writes. Declaring a
new exemption is a change of that list, with its reason, and a line in this
section.

**Commit 6.2, 2026-11-17: `declaration.write`.** The operation is registered
at the Kernel's bootstrap (`aistack.transaction.engines.declaration_write`).
It writes the whole file beside its name and moves it into place; when the
file held something else, it is kept as `<name>.avant-<UTC date>-<time>`
first; when the content is the one already there, it writes nothing. The
caller is `aistack.declaration.write_declaration`: it runs the transaction
and records the change in `declaration-change.json` (and its history): when,
who, why, which file, the digest before and after and the copy kept — never
the content. The first declaration to go through it is the SSH user names of
the network discovery screen; `network_discovery/yaml/store` no longer writes
(it renders the text), which takes the baseline from 33 to 32. The other
declarations follow, one at a time.

**The CPU priorities** (`priority/yaml/store`) follow in the same commit
series: the screen's save and the troubleshooting fix both write through
`write_declaration`; the store renders the text with its comments and no
longer writes (baseline 32 → 31).

**The selection of a pair** (`selection/yaml/store`): the sync screen's save
(`sync/screen.record_selection`) writes through `write_declaration`, with the
person as author; the store renders the text (baseline 31 → 30).
`sync/screen` stays in the baseline for the report of the last application,
which is the service's own state and is declared exempt (§ 11) until it moves
with `selection.materialise` (6.3). `selection/screen.save_and_materialise`,
called by nothing, is deleted with its imports.

**The container declared from the arrivals** (`arrivals/declare`): the text
is still edited by hand-made insertion (the owner's comments and layout stay)
and read by the real loader (`parse_service_categorization_yaml`) *before*
anything is written; then it goes through `write_declaration`, which keeps
the copy under the name the screen has always announced
(`service_categorization.yml.avant-arrivals-<date>`, hence the payload's
`copy_label`) and records who declared what (baseline 30 → 29).

**The place chosen for the data** (`instance/data_location`) closes 6.2:
choosing a disk and forgetting the choice both go through
`write_declaration`. Forgetting takes the file away, which is the same
operation with no content (`content=None`): the previous file is kept and the
change recorded (baseline 29 → 28). The dated copies (`<name>.avant-…`) are
ignored by git (`*.avant-*`): in an installation without a configuration
directory the declarations sit in the checkout, and a copy there must not make
the tree dirty. The six declarations that § 11 lists now go through a
transaction; `sync/screen` stays in the baseline only for the report of the
last application (6.3).

**Commit 6.3, 2026-11-17: `selection.materialise`.** The hard links of a
device's folder are made by the operation of that name
(`aistack.transaction.engines.selection_materialise`), the one place that
links, unlinks and prunes. What it would do is decided by
`generators/filesystem/hardlink.plan_materialisation`, which writes nothing
(`preview_materialisation` is its report, for the screens' *pending* line);
the same per-target lock covers both. A refusal (capacity, another
filesystem, a missing library) comes back as the report's `refused`, a file
that cannot be linked in its `failed`, as before; only an unexpected error
fails the transaction (`MaterialisationFailed`). `hardlink.py` leaves the
baseline of writes (28 → 27). The report of the last application stays
written by `sync/screen` (the service's own state, exempt).

`cli/sync_apply`, the host executor, now builds the Kernel to run the
operation. The owner decided (2026-11-17) that it is exempt like `dock`: an
action command that changes the host through the Kernel's transaction,
started every two minutes by its timer; it joins `dock` and the web
application in the baseline of *an entry point builds the Kernel and never
executes through the Runtime* and leaves *never builds the Kernel* (17 → 16).

## The refactoring plan of August 2026

`AIStack-Refactoring-Plan` (draft v1, 2026-08-13) was the first plan to
bring the bootstrap within the principles. It was never a governed
document and none of its boxes was ticked. Read against the tag and
against `main`:

| Phase | Subject | State |
|---|---|---|
| 1 | Clean the heritage: one definition per concept, no transport artifact left | done at the tag, 2026-08-20 and 2026-08-21 (`fa0fc00`, `6569f91`, `748b1c6`) |
| 2 | One responsibility per concept: repository, Context Bundle, README | done at the tag: *the Context Bundle is the Knowledge Package of AIStack*, 2026-08-29 |
| 3 | The README as bootstrap specification | not in `main`: the README of 2.0.0 presents the product |
| 4 | A Knowledge Acquisition Protocol as a Foundation concept | never written: the term appears in no governed document, at the tag or in `main` |
| 5 | One Boot Report | verified once, `STD-0300` 2.1, 2026-08-14; not verifiable in `main` |
| 6 | Knowledge integrity | built — nineteen checks — and removed on 2026-10-10 |
| 7 | The Context Engine implements the protocol | never built |
| 8 | Onboarding tested with several models | `STD-0300` 2.4, never verified |

Phases 3 to 8 are lot 8 of this decision. Phase 4 is decided there, not
here: whether the protocol becomes a Foundation concept is the owner's.

## Consequences

- A session working in `main` reads the principles in `main`.
- Five weeks of the project have no open-state register. `GOV-0002` 2.0
  says so and does not reconstruct them.
- `STD-0300` no longer reads 17 of 22. For 2.0.0: 2 verified, 9 satisfied
  before 2.0.0 and not re-run, 6 not verifiable in `main`, 5 not
  verified.
- Two architecture guards passed on nothing until lot 5 (`OS-089`); since
  5.3 the Runtime exists and a command boots it, and a test fails if either
  guard looks at nothing again.
- The audit measures imports and citations. It does not tell a generated
  artifact from a modification of knowledge, and it does not verify that
  a chain which builds the Kernel runs through it.

## Open points

- Of the nine criteria of `STD-0300` named by `GOV-0002/OS-091`, three (4.4,
  4.5, 4.9) were re-run on 2.0.0 on 2026-11-17; 1.1 to 1.4, 4.2 and 4.8 have no
  chain to re-run through (`STD-0300` § *Re-run on 2.0.0*).
- The sync links names Syncthing renames (NFD to NFC) and does it again at every
  pass (`OS-094`).
- `OPS-0009` and `QUAL-0001` are cited and were never documents under
  `docs/` (`OS-092`).
- The volume of the traces, to measure on the host after a few days of the
  chains, before the web application executes a Task: lot 5.8 passes it its
  Kernel's providers and executes none.
