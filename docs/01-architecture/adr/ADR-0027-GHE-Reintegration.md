---
artifact:
  id: ADR-0027
  title: GHE Reintegration
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.42
  status: Accepted
  owner: Architecture
  created: 2026-11-15
  updated: 2026-11-18

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
| 7 | The declarations edited by hand on the host become governed knowledge (§ 12), closed 2026-11-17 | — |
| 8 | Self-onboarding: host executors, Context Bundle, boot report (§ 13) | VS-2 of `STD-0300` |

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
Syncthing renames the NFD names the sync links): `OS-094`, fixed by commit 6.7
(the target is named in NFC) and closed the same day, measured on the MSI
(`+0 ~0 -0 =6584` at two passes).
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

### 12. A declaration edited by hand on the host is observed and recorded

`GOV-P-002`. Lot 7, commit 7.1, read on 2026-11-17. The package ships 25
declarations (`src/aistack/*/definitions/*.yml`); the host keeps a copy of each
in its configuration directory (`./config`, `/config` in the container), which
replaces the shipped file, and which `.gitignore` leaves out of the repository.
Of the 25, three change from a screen through `declaration.write`
(`resource_priority.yml`, `network_discovery.yml`, `service_categorization.yml`),
two from the installation assistant (`instance_config.yml`,
`authentication.yml`, exempt, § 11) and twenty only by hand. A hand edit leaves
no author, no reason, no copy of the previous file and no trace; most paths
are fixed at the import of a module, so an edit takes effect at the next start
of the service.

Decided by the owner, 2026-11-17:

- **The edit stays by hand.** AIStack observes and records it; it does not
  oblige the owner to go through a screen or a command.
- **What is recorded**: when, which file, the digests before and after, the
  author as "by hand on the host", never the content. The previous content is
  kept as `<name>.avant-observe-<date>`. A file written by `declaration.write`
  (its digest is the `after` of the last record) is not recorded a second time.
- **An invalid file is reported**, never refused and never restored: a finding
  of the Cockpit names the file, the line and the last valid copy.
- **The 25 declarations**, none excluded: they hold no secret (the API keys are
  in the data directory, `secrets/api_keys.json`).
- **Observed at the start and by the vigil**, as a Task through the Runtime.

Commits: 7.2 `declarations.observe`, 7.3 the validation of each declaration
by its own loader (first, a test per declaration of what an invalid file does
today), 7.4 the list on the Settings page (7.4a: the vigil's Gotify message, 7.4b: the section, 7.4c: a tie-break found on the host), 7.5 the closing. Versioning
`/config/` in the repository is not part of the lot.

**Commit 7.2, 2026-11-17: `declarations.observe`.** The seventh chain the
Runtime executes (`aistack.tasks.declarations_observe`): it reads, compares each
shipped declaration's file in the configuration directory with its snapshot
under `declarations/seen/` of the data directory, and returns digests, never
content. `aistack.declaration.observe.apply` moves the snapshots and records the
hand edits through `declaration.write` (`record=False`: the stream
`declaration-observed` is its own); the previous content is kept as
`<name>.avant-observe-<date>`. Three cases: *reference* (first sight, no change
invented), *follow* (the digest is the last `after` of `declaration-change`: a
screen wrote it, not recorded twice), *edited*. A file that is not UTF-8 is
reported and left alone; a file that changed again since it was observed waits
for the next pass. `aistack.cli.declarations_observe` joins the vigil's pass
(every 15 minutes, and at its start): one more trace per pass, like the health
and console renders. The audit does not move.

**Commit 7.3, 2026-11-17: an invalid declaration is reported.** Measured on
the 25 loaders before writing: a syntax error always raises; a list where a
mapping is expected raises everywhere except `load_api_keys` (fixed: it now
says "not a mapping"); an empty file is accepted by eight loaders (api_keys,
arrivals, cmdb_probe_targets, dock, hosts, infrastructure_topology,
restart_watch, sync), which is their own business. `aistack.declaration.validate`
maps each shipped declaration to its loader (a test fails if a declaration has
none) and returns the loader's own words, shortened, with the line for a YAML
error, never the content. `declarations.observe` returns the `invalid` list;
the CLI prints `! <file> is not read by its loader: <why>` with the last copy
the loader does read (`<name>.avant-observe-*`), and exits 1 so the vigil logs
it. Nothing is refused, nothing is restored (decision 2). Each hand-edit record
gains `valid`, `error` and `last_valid_copy`. The surface that shows it to the
owner is the next commit.

**Commit 7.4a, 2026-11-17: the vigil says it.** The owner chose Settings and
Gotify; no Cockpit domain (adding one touches the score weights, the labels,
the translations and the troubleshooting facts, and `compute_health_score`
raises for a domain with no declared weight). `declarations_observe` keeps what
is invalid now in `declaration-invalid.json` (with its history), written at
every pass, an empty list included, and without a time so that an unchanged
state adds no copy. `notify.events` takes it: a declaration that stops being
read is one urgent event, said once, with the loader's words and the last valid
copy; read again then broken again is said again; the first pass of a fresh
install only notes. `State` keeps the names (`invalid`). The audit does not
move: the file goes through `write_artifact_with_history`.

**Commit 7.4b, 2026-11-17: Settings shows it.** A section "Declarations edited
by hand" follows "Shipped declarations" (administrators, container with a
configuration directory, read only). It lists first what the loaders do not
read *now* (computed live against the configuration directory, with the last
copy that was read), then the recorded edits, newest first (20), each with its
difference: the copy kept before (−) against what the file held after (the next
edit's copy of the same file, or the snapshot for the last). `observe.hand_edits`
reads the stream `history/declaration-observed`; a copy that is gone gives a
difference against nothing, not an error. The difference shows the owner his own
edit: the records never hold content, the files in his data directory do.

**Commit 7.5, 2026-11-17: lot 7 closed.** Measured on the host (the MSI, code
from `8de9669`, a script that plays the whole scenario in a temporary directory:
no real file touched, no Gotify message sent): first sight gives two references
and invents no change; a valid edit is recorded with its copy (exit 0); a broken
file is reported with the loader's words and the last copy it reads (exit 1);
the vigil says it once, urgently, and not again at the next pass; the repaired
file empties the state (exit 0); no record holds the edited text. On the
laptop the suite gave the same, and one defect that only the host showed: three
edits in the same second came out in the order of the files on the disk (7.4c).
The lot closes no entry of `GOV-0002`. What the host measurement could not
show waits for the next `dev` image, which only the owner builds: the Settings
section in a container, and the observation by the `vigil` service itself (the
containers still run the code of before lot 6). The audit did not move during
the lot: no write outside a transaction, 26 declared exempt.

### 13. The Context Bundle and the boot report return

`GOV-P-002`. Lot 8, commit 8.1, read on 2026-11-17 (`main` at `bd7125c`). The
"host executors" of the lot's title are done: `dock` and `cli/sync_apply` build
the Kernel since lots 5 and 6 and are exempt by decision. What is left is what
the tag held and `main` lost on 2026-10-10: the Context Bundle, its official
export script (`scripts/export_project_sources.py`, `ADR-0006`), the knowledge
integrity checks (nineteen at the tag, `aistack.cli.knowledge_integrity`) and
the Boot Report. `STD-0300` VS-2 2.1, 2.2, 2.3, 2.5 and 2.6 read "not
verifiable in `main`"; 2.4 was never verified.

**Decisions of the owner, 2026-11-17:**

- **Scope: everything comes back, by stages.** Read again on 2026-11-17 against
  the tag's file list, the order is: 8.2 the Context Bundle (8.2a the contracts
  and `aistack.conformance`, 8.2b the engine and the official export script,
  8.2c the SSH transfer if the owner still uses it), 8.3 the integrity checks,
  one at a time, as a Task of the Runtime (they read a bundle, so the bundle
  comes first), 8.4 the Boot Report and the protocol, 8.5 the four documents
  (`ADR-0005`, `ADR-0006`, `ADR-0007`, `ARCH-0013`), which return when the code
  they describe does, 8.6 `STD-0300` VS-2 re-run, 8.7 the closing (`OS-088`,
  `STD-0300`). Nothing returns without a use (rule 5): a check returns when
  something runs it. `aistack.package_manager` (thirteen files at the tag) has
  no use in any decision above: it is decided with `ARCH-0013`.
- **The Knowledge Acquisition Protocol becomes a Foundation concept**, written
  in this lot (phase 4 of the August plan; it appears in no governed document
  today). It describes the acquisition states and the Boot Report; the code
  that returns implements it, the text stays independent of any technology.
- **The README stays a presentation of the product.** Phase 3 of the plan (the
  README as bootstrap specification) is not done: the AI's bootstrap is carried
  by the Context Bundle and the Boot Report.

The tag's files come from the owner (`git show <tag>:<path>`): Claude does not
reach the tag. Versioning stays as in lots 5 to 7: one commit, one patch, the
host measures at the end.

**Commit 8.2a, 2026-11-17: the contracts and `aistack.conformance` return.**
Nine contracts the bundle names and `main` lacks (`knowledge_registry`,
`discovery`, `criticality`, `classification`, `artifact_builder`,
`registry_builder`, `readme_exporter`, `eligibility`; `manifest_serializer`
waits for 8.2b, it imports the bundle manifest) and the package that measures
whether a class satisfies a contract (`structural`, `inventory`, `registries`,
`serialization`, `registry_serialization`), with its 56 tests. The four
contracts `main` already holds (`artifact`, `undeclared`, `registry_inventory`,
`contract_inventory`) were compared to the tag's: the same code, only the
comments were shortened; `main`'s stay. `contract_inventory` and
`registry_inventory` had no user in `main`: the inventory is theirs. Two
adaptations, both written here: the inventory no longer wraps its walk in the
quarantine's `inspecting()` (the quarantine of `OPS-0012` is not in `main`), and
two tests changed: `test_the_integrity_checks_satisfy_their_contract` comes
back with the checks (8.3), and the file the repository test looks for is
`kernel/bootstrap/registrations.py` (the tag had `providers.py`).

**Commit 8.2b, 2026-11-17: the Context Bundle engine and the export script
return.** `aistack.context_bundle` (discovery, eligibility, builders, registry,
generation, manifest, export, `engine`, `service`) with seven contracts
(`context_bundle`, `context_bundle_builder`, `context_bundle_engine`,
`context_bundle_service`, `bundle_manifest`, `bundle_exporter`,
`bundle_export_manager`), `manifest_serializer`, and `scripts/export_project_sources.py`
with their tests (67 more in the suite). Four decisions, written here:

- *The transfer is not there.* The script no longer imports the SSH transfer;
  `service` keeps its optional `transfer_service`, and the one-method contract
  `context_bundle_transfer_service` comes with it because the service and its
  isolation tests name it. Whether `transfer/` returns is 8.2c, and depends on
  whether the owner still pushes the bundle to another machine.
- *The export writes the projection, and that is declared exempt* (the
  category `PROJECTION`, three files: the JSON, Markdown and zip exporters).
  § 11 says the principle governs a modification of knowledge and what a
  person's choice triggers on the host; the bundle is a derived projection,
  written whole at each run and never edited, as `generators/history` is
  for generated artifacts. Baseline `disk_writes_declared_exempt` 26 → 29,
  `disk_writes_outside_a_transaction` stays empty. This is a declaration of
  the owner's list, made here for him to confirm by applying the patch.
- *`OPS-0002` had lost its frontmatter* when it was condensed for 2.0.0, so the
  bundle carried it as `unknown` beside the README and refused two artifacts
  without an identifier (`Knowledge artifact already registered: unknown`).
  It declares now `id`, `title` and `version`; its domain, criticality and
  owner are the owner's to qualify (FDN-0003 Article 4), they read `unknown`.
- *The export test writes elsewhere than in the repository.* The script's
  `AISTACK_BUNDLE_OUTPUT_DIR` is used by the test, which also checks that no
  `context/` appears in the tree.

Two tests wait for 8.3 because they read the bundle with
`aistack.integrity.bundle_reader`: `test_contract_inventory_travels` and
`test_identity_survives_the_projection`.

**Commit 8.2c, 2026-11-17: the SSH transfer does not return.** The owner's
answer: the bundle serves to know the context; once it is available where it
is read, it is no longer pushed to another machine. `context_bundle/transfer/`,
`sync_context_bundle.sh`, `config/context_bundle_transfer.yml.example` and
`ADR-0007` (the transfer) stay at the tag. `service` keeps its optional
`transfer_service` seam (8.2b), nothing builds one.

**Commit 8.3, 2026-11-17: the integrity checks return, run by a Task.** The
bundle reader (`aistack.integrity.bundle_reader`), the engine, the three
contracts (`integrity_check`, `integrity_finding`, `integrity_report`) and the
eighteen checks of the tag, with their tests, come back unchanged but for two
comments that cited an identifier invented for the case. The command
`aistack.cli.knowledge_integrity` is now a thin caller of the eighth Task,
`knowledge.integrity` (`aistack.tasks.knowledge_integrity`, no provider): the
Task reads the projection and returns what each check observed, the command
prints the same report and keeps the same exit codes (1 when something blocks,
2 when the bundle is not there); a trace is kept under `reports/generated/` of
the working directory. The eighteen came together, not one by one as planned:
the engine composes them (`test_default_composition_is_stable` pins the list),
the Task runs them all, and every one passed untouched; the owner can send one
back by removing its line from `default_checks()`. The control case returns
with them: `IntegrityCheck` is satisfied by eighteen classes
(`test_the_integrity_checks_satisfy_their_contract`), and the two bundle tests
held at 8.2b (`test_contract_inventory_travels`,
`test_identity_survives_the_projection`).

*Two adaptations written here.* The audit no longer reads the tests of the
integrity checks as citations (`FIXTURE_TESTS`, as it already skips its own
test): a check that reads identifiers is tested on identifiers invented for
the case. The test of the command runs in the bundle's folder, so that its
trace is not left in the repository.

*Measured on `main`, 2026-11-17* (bundle exported from the tree, then the
command): 60 artifacts, **0 blocking, 15 warnings**. The warnings are the
README, which declares no metadata block, and a few artifacts without status,
domain, semantic type or criticality (`OPS-0002` since 8.2b, to qualify by the
owner), plus 4 accepted decisions without a readable implementation state. The
observations are the facts the checks state (13 of 32 contracts satisfied by
no class, 13 references designating no artifact, 88 undated assertions).

**Commit 8.4, 2026-11-17: the Knowledge Acquisition Protocol is written; there
is no Boot Report code to return.** The tag, listed by the owner for `boot`,
`acquisition`, `protocol`, `kap` and `onboard`, holds no program that produces a
Boot Report: only `FDN-0009`, already in `main`, the Kernel's bootstrap, and a
session note. The Boot Report was always a document an agent writes after
reading the bundle (`STD-0300` § VS-2, criteria 2.1 to 2.3), and the Context
Engine of the August plan was never built. So 8.4 is writing, not returning:
`FDN-0013 — Knowledge Acquisition Protocol`, a Foundation concept, `Draft`
v0.1, indexed in `FDN-0001`. It holds the five principles, the two points of
truth (Governance SPOT, Acquisition SPOT), the seven acquisition states, what
the protocol produces (an Operational Context, no recommendation) and the Boot
Report in eight sections with the rules `FDN-0009` already records. It says what
implements it today (the bundle and the integrity Task; the agent does the
rest) and that the Context Engine is not built.

It is a proposal of the assistant, to be validated by the owner (`GOV-P-001`):
four open points are written in it, none decided: the rule that makes a verdict
NOT READY, where an agent finds the protocol (the bundle's README presents the
product and does not point to it, and `FDN-0009` still says acquisition belongs
to an "AI Boot section of the README" that `main` does not have), the
qualification of the document, and criterion 2.4. `FDN-0009`, `Published`, is
left unchanged: correcting its sentence is the owner's decision with the
document's engraving. Measured: the bundle now carries 61 artifacts and the
integrity check still reports 0 blocking and 15 warnings (the new document is
complete); `clean: True` (criterion 2.6) needs those 15 warnings answered, which
is for 8.6.

**Commit 8.5, 2026-11-18: three documents return, `package_manager` stays at the
tag.** `ADR-0005`, `ADR-0006` and `ARCH-0013` come back from the tag, read
against `main` (lot 8.2b put the code they describe back). Each carries a dated
section and is not rewritten. `ADR-0005`: the engine and the script are in
`main`; the script takes no transfer (decision of 2026-11-17). `ADR-0006`: three
statements are no longer true and are corrected under their date, namely the
"configured transport layer", the claim that a suite run regenerates the
projection (the test now writes to a temporary folder) and the publication order
(`ruff`, `mypy`, `pytest`). `ARCH-0013` stays `Draft`; its section of
2026-09-23 describes a code that is not in `main`, and the new section says so.
`ADR-0007` (the transfer) does not return and joins `FDN-0001` § *Kept at the
tag* (`docs/01-architecture/adr/`).

**Decided by the owner, 2026-11-18 (option A): `aistack.package_manager` stays at
the tag.** Thirteen files and five tests; nothing in `main` calls it, no
decision above needs it (rule 5), and its integration engine writes the working
tree directly, which would add a write outside a transaction (§ 11). It returns
if a real case for a receiving dock appears, with its use. The four open points
of `ARCH-0013` stay open.

Measured: `documents_cited_and_absent` is empty (4 then 0); `OS-088`, whose
list this was, can close at 8.7.

**Commit 8.6a, 2026-11-18: the fifteen integrity warnings are answered.** The
check on the bundle (64 artifacts) reported 0 blocking and 15 warnings, which
come from three subjects: `OPS-0002` (nine missing fields of its metadata block,
four of them shared with the README), the README (no metadata block) and four
accepted decisions without an implementation state (`ADR-0024` to `ADR-0027`).
`OPS-0002` and the README get back the block they carried at the tag, with the
owner's values (`OPS-0002`: *Operations Procedure*, `Policy`, `Operations`, C2,
`Draft`, owner `Operations`; README: `README-AISTACK`, *Entry Point
Documentation*, `Knowledge Artifact`, `Foundation`, C2, `Draft`, owner
`Foundation`). The four decisions get a measured `## Implementation state`
section: `ADR-0024` is *not started* in all five rows by decision;
`ADR-0025` and `ADR-0026` are *done* in code, with what a real run has not
shown written beside it; this decision's own table is the one above.

Measured after: the same bundle, 64 artifacts, **0 blocking, 0 warnings,
`clean: True`** (the exit code is 0). The observations grow where the new tables
say a decision is unfinished (`unfinished-decisions`: 8 rows, then 14); they are
the register's to qualify, not faults. `OPS-0002` lists only the references that
exist in `main` (`ENG-TEST-0002`, `GOV-0002`); `FDN-0005`, which it cited at the
tag, stays at the tag.

**Commit 8.6b, 2026-11-18: criteria 2.5 and 2.6 of `STD-0300` are verified by the
suite.** The test that executes them
(`tests/integration/validation/test_std_0300_scenario_2.py`) returns from the
tag, without the variable that disabled the transfer (the transfer does not
return). It passed on `main` untouched. `STD-0300` 1.30: 8 verified, 6 satisfied
earlier and not re-run, 3 not verifiable in `main` (2.1 to 2.3, which ask an
agent for a Boot Report), 5 not verified.

*The other seven files of `tests/integration/validation/` stay at the tag for
now.* Run on `main` as they are, six of their tests fail, and none of the
failures is a defect found: floors measured in August (65 artifacts, 19 types,
39 declarations, 29 register entries) that the smaller heritage of `main` does
not reach; twelve references to documents declared kept at the tag; and the
dates of forty returned documents, which the test reads against a git history
that starts on 2026-11-15. Each needs a re-measure or a decision of the owner,
not a quiet change of the number.

**Commit 8.6c, 2026-11-18: the contract inventory sees the Context Bundle
packages.** The agent that ran the VS-2 scenario from the bundle alone reported
that 13 of the 32 contracts read "satisfied by no class". It was not the code:
`satisfies(DefaultContextBundleEngine, ContextBundleEngine)` is true. The
packages `aistack.context_bundle` and six of its seven subpackages had no
`__init__.py` (the tag had the same gap), and `take_inventory` walks packages
with `pkgutil.walk_packages`, which skips directories without one. The seven
files are added, empty. The inventory goes from 565 to 593 modules and from 377
to 394 implementations; three contracts still read "satisfied by no class"
(`ContextBundleTransferService`, `Receiver`, `Writer`), which is true: the
transfer does not return, and no class in `main` implements the two transport
interfaces. The audit measures are unchanged.

## Implementation state

Measured 2026-11-18, at `abcdb90`.

| Step | State |
|---|---|
| § 1 The core of the principles returns to `main`, the rest stays at the tag (lots 0 to 2) | done — 2026-11-15 |
| Lot 3 No technology in the Kernel (§ 7) | done — 2026-11-15 |
| Lot 4 Application code asks the Kernel for a provider (§ 9) | done — 2026-11-15 |
| Lot 5 The chains run through the Kernel as Tasks (§ 10) | done — 2026-11-17 |
| Lot 6 Modifications of knowledge go through a transaction (§ 11) | done — 2026-11-17 |
| Lot 7 The declarations edited by hand on the host are observed (§ 12) | done — 2026-11-17 |
| Lot 8 The Context Bundle and the boot report return (§ 13) | not done — 8.1 to 8.5, 8.6a, 8.6b and 8.6c done 2026-11-18; the grading of `STD-0300` 2.1 to 2.3 and 8.7 (closing) remain |

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
- `OPS-0009` and `QUAL-0001` are cited and were never documents under
  `docs/` (`OS-092`).
- The volume of the traces, to measure on the host after a few days of the
  chains, before the web application executes a Task: lot 5.8 passes it its
  Kernel's providers and executes none.
