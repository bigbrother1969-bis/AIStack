---
artifact:
  id: GHE-IN-AISTACK
  title: Governed Heritage Engineering in AIStack 2.1
  type: Handbook Guide
  semantic_type: Knowledge Artifact
  domain: Foundation
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Foundation
  created: 2026-11-18
  updated: 2026-11-18

relations:
  references:
    - FDN-0004
    - FDN-0008
    - FDN-0012
    - ADR-0027
    - GOV-0002
    - RELEASE-NOTES
---

# Governed Heritage Engineering in AIStack 2.1

## Purpose

AIStack 2.1 brings back, inside the product, the principles the project says it
follows — and makes the code answer to them. This page explains, one concept at
a time, **why** each came back, **how** it works, and **what you can see** of it.

It is written for someone who runs AIStack or reads its code, not for someone who
already knows the governance vocabulary. The decisions themselves, with their
measures and their dates, are in `ADR-0027`; the release notes say what changed
version by version.

## What Governed Heritage Engineering is

The Foundation documents define it (`FDN-0004`, `FDN-0008`): an infrastructure is
understood and handed on only if what is known about it is a *governed heritage* —
dated, sourced, owned, explained, never overwritten. And a system that claims to
build such a heritage for others **must first govern its own**. AIStack is its
first user: its own rules, decisions, figures and code are held to what it asks
of the infrastructures it observes.

## Why 2.1

On 2026-10-10, before 2.0.0, the project removed from `main` what nothing in the
product ran: the heritage is whole at the tag `archive/heritage-2.0.0-rc1`, and
`main` kept only the documents that describe the product. That was right for
2.0.0. But two things left with it that the product still depended on:

- **The principles.** The code cites them by identifier — `ARC-P-006` 46 times,
  `GOV-P-001` 23 times — and the registry that defines them, with the
  Constitution, the Glossary and the Manifesto, was no longer beside it. Someone
  working in `main` could not read what they were asked to respect.
- **The check.** The knowledge-integrity validator was the only thing that
  verified the heritage. Nothing replaced it.

And the code itself had drifted from the principles it cited. Measured on
2026-11-15, the day the work was decided, by a script written that day
(`scripts/ghe_audit.py`):

| What the principles forbid | On 2026-11-15 | In 2.1.0 |
|---|---|---|
| A technology named inside the Kernel | 10 imports leaving the Kernel, 6 of them naming a technology | 0 |
| A command that never goes through the Kernel | 22 of 25 entry points | 16, each a declared exception (permanent monitors, status commands) |
| A registered Task that nothing executes | 1 | 0 |
| Application code building a provider itself | 23 pairs of a file and a provider | 7, the providers configured at each use, declared |
| The disk written outside a transaction | 35 files | 0 outside; 29 declared exempt, each with its reason |
| A document cited and absent from the tree | 22 | 0 (what stays at the tag is declared) |

The project's own Manifesto forbids the obvious answer — *preserve working
heritage; migrate incrementally; do not rewrite functioning code because a
cleaner architecture exists* — and 2.0.0 was in production with a green suite.

## How the work was done

Four rules, decided by the owner on 2026-11-15, and kept to the end:

1. **The core returns, the rest stays at the tag.** Not everything — that would
   undo the decision of 2026-10-10 and bring back some 58,000 lines, much of it
   unexecuted.
2. **Nothing returns without a use.** A document returns when it is read or
   verified; a module returns in the lot that executes it. This is the rule that
   left some things behind on purpose (see the end of this page).
3. **The departures are measured, and the list only gets shorter.** The audit's
   result is recorded in `tests/reference/ghe_audit_baseline.json`; the suite fails
   on a departure that is not in it, and on a recorded departure that no longer
   exists.
4. **Lots of small, reversible steps.** Each lot is a series of atomic commits
   validated on the production of 2.0.0: suite green, health cockpit unchanged,
   generated artifacts compared before and after. The owner decides at the end of
   each lot.

Nine lots, from the heritage in sight (lots 0 to 2) to the Context Bundle (lot
8), delivered between 2026-11-15 and 2026-11-18.

## The concepts

### 1. The heritage is in sight

**Why.** A rule nobody can read is not a rule. The code said `ARC-P-006` in its
comments and the file that says what `ARC-P-006` means was at the tag.

**How.** The Constitution, the Glossary, the Manifesto, the principles registry
(`FDN-0012`), the protocols and the standards that govern the project's own
documents are back in `docs/`. What stays at the tag is listed in one place —
`FDN-0001`, § *Kept at the tag* — and a citation of one of those documents leads
there; no citation was rewritten.

**What you see.** Nothing in the product. In the repository, every principle the
code cites can be opened.

### 2. A Kernel that names no technology, and that builds itself from a list

**Why.** The Kernel is the core every chain runs through. If it names Docker, a
sync tool or a media format, it can no longer be reasoned about, tested or changed
without touching a technology (`ARC-P-001`, `ARC-P-004`). And if it wires each
provider by hand in its own code, adding one means changing the Kernel
(`ARC-P-002`).

**How.** The Kernel may name a *generic mechanism* — the transport, the
transaction, the history — never a technology. What it registers when it boots is
read from a file outside it, `src/aistack/registrations.yml`: providers, catalog
views and Tasks, one line each. Adding a provider is a line there, never a change
to the Kernel. The cost, said once: a line that names a class that does not exist
fails when the Kernel boots, where an import used to fail when the module was
read; a test of the suite checks every declared path.

**What you see.** Nothing, as long as it works. That is the point.

### 3. Application code asks the Kernel for a provider

**Why.** Twelve providers existed, two were registered, and ten files of
application code built their own. Observation then escapes the Kernel: it cannot
say which providers exist or how they are configured (`ARC-P-002`; and
`ARC-P-012` — providers observe and collect, they never decide).

**How.** The health, console and troubleshooting chains and the priority screen
ask the Kernel for their providers. Seven pairs remain, by decision: providers
configured at each use (a probe, a Beszel endpoint), built where their
configuration is read, and declared in the audit's baseline.

**What you see.** Nothing.

### 4. Chains run through the Runtime, as Tasks, and leave a trace

**Why.** A chain that runs outside the Runtime leaves no record of what ran, when,
on what request. The principle says the Kernel orchestrates; until 2.1 nothing
did: the Runtime had been removed with the heritage, and the one registered Task
was reached by nothing.

**How.** A chain passes through the Kernel when it is a Task declared in
`registrations.yml`, executed by the Runtime from a Request, with a trace kept.
The command or the page becomes a thin caller. Eight Tasks run this way:

| Task | What it does |
|---|---|
| `health.render` | the health cockpit |
| `architecture.render` | the architecture page |
| `console.render` | the console |
| `timemachine.rebuild` | the Time Machine's graph |
| `network_docker.discover` | the scan of the machines |
| `ai.reason` | the AI's reasoning on a finding |
| `declarations.observe` | the observation of the declarations (concept 6) |
| `knowledge.integrity` | the integrity check (concept 7) |

Some things do not become Tasks, on purpose, and are declared as exceptions: the
permanent monitors (a daemon that listens without end is not a Request that
returns an Observation), the status commands that only read (`healthcheck`,
`hosts`, `data_budget` — a trace at each consultation would add nothing and grow
the history), the executors of the host (`dock`, `sync_apply`, which act through
transactions) and the web application, until a screen executes a Task.

**What you see.** Each run keeps a trace under
`reports/generated/history/execution-trace/`: what asked, when, what came back —
never a secret, never the content of a file. The vigil's passes now leave some. On
the selection screen, each line also says which rule decided it (ticked, covered
by a parent, inherited, excluded): that explanation, which 2.0.0 had lost, came
back in the same lot.

### 5. A modification of knowledge is a transaction

**Why.** When you change a declaration from a screen, you change what AIStack
believes about your infrastructure. If the file is half-written, or replaced with
no copy, no author and no reason, the heritage has a hole that nothing shows
(`GOV-P-002`: every modification is a governed transaction; `GOV-P-003`: atomic,
complete, reproducible).

**How.** One operation, `declaration.write`, now carries every declaration a
screen changes: the CPU priorities, a pair's selection, the SSH user names, a
container declared from *Nouveautés*, the place chosen for the data. It writes the
whole file or nothing; keeps the previous one as `<name>.avant-<date>-<time>`; writes
nothing when the content is identical; and records who, when, why and the
fingerprints before and after (`declaration-change.json`) — never the content.
The hard links of a selection, which change what sits on a device's folder, have
their own operation, `selection.materialise`.

The principle governs *knowledge* and *actions on the host that a person's choice
triggers*. It does not govern what a service keeps for itself: service state,
locks, the installation, maintenance, API keys (which are kept apart from every
trace), and the three exports of the Context Bundle, which are projections. These
29 files are **declared exempt**, each with its reason, and measured like the
rest.

**What you see.** A dated copy next to a file a screen changed. And a fault the
verification on the host found on the way: a file whose name carries an accent was
linked and removed again at every sync pass — seven files each time — because
the library wrote the name one way and the target folder rewrote it another
(Unicode NFD against NFC). It had been there since before the lot; the sync now
names the target in NFC and a second pass changes nothing.

### 6. A declaration edited by hand is observed

**Why.** AIStack ships 25 declarations; the host keeps a copy of each, which
replaces the shipped one. Twenty of them are edited only by hand. A hand edit
leaves no author, no reason, no copy of the previous file, no trace — and a
broken file is discovered at the next start of the service, with an error and
nothing else.

**How.** The decision of the owner: *the edit stays by hand*. AIStack does not
oblige anyone to go through a screen; it observes. At each vigil pass (every 15
minutes, and at its start), the Task `declarations.observe` compares each
declaration with the copy it saw last, kept under `declarations/seen/` in the
data directory.

- First sight of a file: it becomes the reference; nothing is invented.
- A file written by `declaration.write` is recognised (its fingerprint is the
  *after* of the last record) and not recorded twice.
- A file edited by hand: the previous content is kept as
  `<name>.avant-observe-<date>`, and the edit is recorded — when, which file, the
  fingerprints, and the author *by hand on the host*. Never the content.
- A file its loader no longer reads is **reported, never refused and never
  restored**: the vigil tells Gotify once, urgently, with the loader's own words
  and the last copy that read; reading it again closes the case.

**What you see.** Settings → *Déclarations modifiées à la main*: what cannot be read
now, and the last twenty edits with their difference.

### 7. The heritage checks itself, and an AI can acquire it

**Why.** Governing someone else's knowledge while one's own cannot be checked is
the contradiction `FDN-0008` forbids: *AIStack applies Governed Heritage
Engineering to itself before applying it to information systems.* And an AI
assistant working on the project needs to know what is governed, from where, and
how sure that knowledge is — without reading the whole repository.

**How.**

- **The Context Bundle** is the portable projection of the governed documents:
  `python scripts/export_project_sources.py` writes it (65 artifacts at 2.1.0), with
  a manifest that says which commit it was taken from and a content hash that does
  not depend on the machine or the time of generation.
- **Eighteen integrity checks** read the bundle — metadata complete, identifiers
  that resolve, decisions that have an implementation state, assertions that carry
  a date, and so on. `python -m aistack.cli.knowledge_integrity` prints what they
  observed and exits 1 when something blocks. It runs as the Task
  `knowledge.integrity`. On 2026-11-18, on the first reading, it found fifteen
  warnings in the documents; they were answered, and the report now reads
  `blocking: 0   warnings: 0   clean: True`.
- **The protocol** (`FDN-0013`, a Draft: its qualification is validated, its text is
  not yet engraved) says how
  an agent acquires that knowledge: two points of truth — the Git repository is
  where the heritage is decided, the bundle is what an agent reads — seven
  acquisition states, and a Boot Report of eight sections ending in READY or NOT
  READY, with its scope. The agent never creates authoritative knowledge
  (`GOV-P-001`): its report is evidence for the human who decides.
- **It was tried.** On 2026-11-18, an agent given nothing but the bundle produced
  that report, stated the commit and the content hash the bundle carries, and named
  the two points of truth and the mirrors correctly (`STD-0300`, 2.1 to 2.3). It
  also found something no check had: the inventory of contracts could not see the
  Context Bundle's packages (seven directories without an `__init__.py`). Fixed.

**What you see.** Nothing in the web application. From a checkout of the
repository, the commands above. The Docker image carries the product, not its
documentation.

### 8. The principles are measured

**Why.** A principle that is only written is a wish. The departures above were
found because someone counted.

**How.** `python scripts/ghe_audit.py` reads the source and the documents and
reports every departure it can measure, in the table at the top of this page. The
suite compares that report with `tests/reference/ghe_audit_baseline.json` and
fails on a new departure and on a recorded one that no longer exists. It verifies
what is cited, registered and imported; it says nothing about the *content* of a
document — that is the integrity checks' work.

**What you see.** A red test the day someone adds a write outside a transaction, a
technology in the Kernel or a chain that never runs.

## What did not come back, on purpose

*Nothing returns without a use.* Left at the tag, and declared:

- the package manager (`aistack.package_manager`, thirteen files): no caller in the
  product, and it writes the repository tree directly — a write outside a
  transaction more;
- the SSH transfer of the Context Bundle to another machine, and the decision
  record that described it (`ADR-0007`): the bundle is read where it is generated.

## What to expect when you upgrade

Nothing to configure. You may notice:

- dated copies next to a declaration a screen changed (`*.avant-*`), kept in your
  configuration directory;
- traces under `reports/generated/history/execution-trace/`, more of them, since
  the vigil's passes now leave some;
- a Gotify message, urgent and once, if a declaration you edited no longer reads;
- a new section in Settings.

And what is still open, said plainly: `FDN-0013` is a Draft; the cross-model
verification of the protocol (`STD-0300`, 2.4) has not been done; and the Context
Bundle names the directory it was generated in in each artifact's `source`
(`GOV-0002/OS-096`, decided for after 2.1).

## Where to read more

- `ADR-0027` — every decision, with the measure that motivated it, lot by lot.
- `FDN-0012` — the principles, and what each one says.
- `FDN-0004`, `FDN-0008` — Governed Heritage Engineering and its self-application.
- `FDN-0013` — the protocol an AI agent follows.
- `GOV-0002` — the register of what is known, decided or waiting.
- `docs/04-handbook/RELEASE-NOTES.md` — what changed, version by version.
