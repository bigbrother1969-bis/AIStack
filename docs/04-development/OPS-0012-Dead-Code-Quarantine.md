---
artifact:
  id: OPS-0012
  title: Dead Code Quarantine
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Operations
  created: 2026-10-05
  updated: 2026-10-05

relations:
  references:
    - OPS-0004
    - OPS-0008
    - ADR-0004
    - ARCH-0010
---

# OPS-0012 — Dead Code Quarantine

## Purpose

This register declares how AIStack removes code nothing uses any more:
not on sight, but after a quarantine long enough to find out whether
something still uses it. Decided by the owner, 2026-10-05, when asking to
clean AIStack of the attempts its first weeks left behind: "on va le faire
prudemment : tu vas d'abord pointer les fichiers effaçables et on va mettre
en place un dispositif de quarantaine. On va surveiller quelques semaines
et ensuite on effacera définitivement."

## Why a quarantine

**An import graph does not see everything a file is for.** The first
inventory, the same morning, followed the imports from every entry point
— the web application, every CLI, the context bundle exporter — and listed
83 modules nothing reached. Read against the governed documents, several
of them were not dead at all:

- `kernel/contracts/registry` and `mutable_registry` are `Protocol`s:
  the classes that satisfy them never import them, and `ADR-0004` names
  them among the Kernel's seven contract modules;
- `location/`, `transport/filesystem/` and `transaction/` are the
  Repositories, the only implementation of the Capabilities, and the
  Transaction Service of the hierarchy the README and `ARCH-0010` declare
  (Applications → Interfaces → Kernel Services → Kernel: Engines,
  Registries, Repositories, Capabilities) — not yet wired, not dead;
- three documents under `docs/99-meta/integration/history/` are cited as
  their source by `ARCH-0012`, `ARCH-0013` and `GOV-0001`.

The owner's questions caught the first two; the third was found by
searching for file names, not paths. What survives such a reading is a
candidate, not a certainty: a crontab, a command typed by hand or a script
on another machine leaves no trace in the repository.

## The register

`src/aistack/quarantine/register.yml` — inside the package, so the
container reads it, but outside any `definitions/` directory, so
`config_init` never copies it into the configuration directory: it
describes the code, not the host. Each entry names:

- `id` — `Q-001`, `Q-002`…;
- `paths` — the files and directories deleted together, relative to the
  repository root (a directory ends with `/`);
- `reason` — why it is believed unused;
- `since` and `review_after` — the entry into quarantine and the date it
  may be deleted from;
- `amend` — the files that name it and have to be corrected in the same
  deletion.

**First entries, 2026-10-05**: eleven items, the lists A1 and A2 the owner
approved, for **six weeks** — review on **2026-11-16**, the owner's choice
("on part sur 6 semaines").

## The tripwires

**Nothing is moved.** A moved file breaks a hidden use at once; a file
left in place with a tripwire reveals it without breaking anything.

- **A Python module** ends — or, for a program, begins — with
  `tripwire(__name__)` (`aistack.quarantine.tripwire`). Imported, it prints
  a warning and appends one line to
  `reports/generated/quarantine/hits.jsonl`: the date, the module, who
  imported it, the command line. It never raises. Imports made while the
  test suite runs are not recorded: the tests of a quarantined module stay
  until it is deleted.
- **A shell script** sources `scripts/quarantine_tripwire.sh` and calls
  `quarantine_tripwire <its path>` before doing anything: the same line,
  with the command that launched it — a crontab shows up there as cron's
  command. The line goes to AIStack's data directory: `AISTACK_DATA_DIR`
  when `.env` names it (docker compose), else `reports/generated`.
- **A document or a data file** runs nothing: the guard below watches it.

## The guard

`tests/unit/quarantine/test_quarantine_references.py`, run by the suite on
the laptop and on GIGABYTE before every push:

- every path of the register is still tracked by git — an entry leaves the
  register in the same commit that deletes its files;
- no file outside the quarantine names a quarantined item — its path, its
  module, or its file name when that name says which file it is — except
  the files its `amend` lists, the register and this policy, the frozen
  heritage (`archive/`), generated reports and the release notes;
- every quarantined Python module and shell script carries its tripwire.

A new dependency on quarantined code therefore fails the tests before it
is published.

## Where it shows

**The health page's "Dette technique" card.** Quarantined code is
technical debt until it is deleted (`OPS-0004`'s ninth reference case):
one finding per item, qualified `OPS-0004/technical-debt` alone, counted
as one more group beside the seven domains — 15 points, once (`OPS-0008`
§ *Technical debt score*). A line under the score says how many items are
in quarantine, the next review date and how many uses were recorded; an
item used, or ready to be deleted, is listed by name.

**`python -m aistack.cli.quarantine_report`** — each item, its state, its
last uses, its review date and what to amend. In a checkout it also says
which paths are no longer there. On GIGABYTE:
`docker compose exec web python -m aistack.cli.quarantine_report`.

## At the review

| State | Meaning | What happens |
|---|---|---|
| watched | no use recorded, review date not reached | nothing |
| used | at least one use recorded, whatever the date | the item leaves the register and loses its tripwires: it is not dead |
| ready | no use recorded, review date reached | one deletion patch: the files, the amendments `amend` lists, the entry |

A deletion is a commit like any other: the owner reviews the patch,
applies it and publishes it. Once the register is empty, the card no
longer counts the quarantine.

## What this register does not do

- It does not decide what goes into quarantine: the owner does, from a
  classified inventory (to delete, to decide, to keep).
- It does not watch what was kept or left to decide in the 2026-10-05
  inventory (`package_manager`, `providers/nextcloud`, `kernel/context`,
  the `CMP-*` component folders…): each enters the register only by the
  owner's decision.
- It does not wire what the hierarchy declares but does not run yet — no
  capability registered at start-up, no Transaction or Context service in
  `KernelServices`. Those are work to do, not dead code.
