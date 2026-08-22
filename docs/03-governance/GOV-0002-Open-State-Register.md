---
artifact:
  id: GOV-0002
  title: Open State Register
  type: Governance Register
  semantic_type: Knowledge Artifact
  domain: Governance
  criticality: C2
  confidence: Declared
  version: 1.4
  status: Draft
  owner: Foundation
  created: 2026-08-22
  updated: 2026-08-22

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
derivable**. The others are declared, because nothing can derive them today.

An entry therefore carries a `derivable` field. When a nature becomes
derivable, its entries stop being maintained by hand and become the output of
a check. The register measures its own automatability, and the first entry
below is precisely the tool that would make the first nature derivable.

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

#### GOV-0002/OS-001 — Seventeen declared contracts are satisfied by nothing

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** open
**Observed** 2026-08-22 at `3166073`. Every `.py` under `src/aistack` imported
by path (277 files, one import failure), yielding 56 contracts — `Protocol` or
`ABC` — and 130 concrete classes. Structural conformance tested with the
helper described in OS-002. Seventeen contracts have no class, anywhere, that
satisfies their members. Ten of the seventeen are one family:
`PackageCapability` and its nine specialisations — `Compress`, `Decompress`,
`Encrypt`, `Decrypt`, `Hash`, `Serialize`, `Deserialize`, `Sign`,
`VerifySignature` — declared together and implemented never. `TransferTarget`
is another: transfer code exists, and implements `BundleTransfer` instead.

*Three earlier measurements of this were wrong and are recorded in the
session log: nominal inheritance (meaningless for structural Protocols), a
structural pass that reported `IntegrityCheck` as orphan while seven checks
implement it, and a claim that `pyproject.toml` omitted ten directories from
the distribution — disproved by building the wheel and reading its contents.*

**Derivable** yes, once OS-002 is resolved
**Qualification** `unknown`. STD-P-002 makes a contract ahead of its
implementation the prescribed order, not a defect. Which of the seventeen are
planned and which abandoned is the owner's judgement, entry by entry.

#### GOV-0002/OS-002 — The tool that measures contract debt is not in the product

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** open
**Observed** `tests/unit/kernel/contracts/conformance.py`, written 2026-08-21
for four kernel contracts. It is the only code that can decide whether a
class satisfies a Protocol structurally, and it lives in the test tree.
**Derivable** no — this is what makes the others derivable
**Qualification** `unknown`. Promoting it to `src/` and adding an integrity
check would make FDN-P-014 operative: the seventeen of OS-001 would be
published by the validator at every projection instead of asserted by an
agent.

#### GOV-0002/OS-003 — `ARC-P-005` and FDN-0011's second principle state one rule twice

**Nature** `contract-debt` · **Opened** 2026-08-21 · **State** open
**Observed** `ARC-P-005` reads *contracts before implementations*. FDN-0011's
second principle, *Contract First Engineering*, says the primary deliverable
of engineering is a governed set of contracts. The same rule at two
altitudes. Recorded in PRINCIPLES-REGISTRY v2.1 rather than resolved, and the
second was deliberately not registered.
**Derivable** no
**Qualification** `unknown` — reword `ARC-P-005` to absorb the fuller
statement, or keep both levels deliberately.

#### GOV-0002/OS-004 — `type` → `domain` is stated and enforced by nothing

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** open
**Observed** STD-0100 v2.1 states that a declared `type` determines its
`domain`. Measured across 63 artifacts and 16 distinct types with no
exception. No integrity check verifies it; it holds because it has been
applied by hand.
**Derivable** yes — a check comparing declared types across the bundle
**Qualification** none required; the rule is decided.

#### GOV-0002/OS-005 — The `<DOMAIN>-P-NNN` convention is enforced by nothing

**Nature** `contract-debt` · **Opened** 2026-08-21 · **State** open
**Observed** STD-0102 v2.0 renumbered every principle to `<DOMAIN>-P-NNN`.
Writing `FDN-006` in PRINCIPLES-REGISTRY tomorrow would pass every check.
The renumbering itself missed the Operations family — four principles and one
citation — and that gap survived a day undetected.
**Derivable** yes — a check over the registry's identifiers
**Qualification** none required; the convention is decided.

#### GOV-0002/OS-017 — A sentence about the code can become false and nothing sees it

**Nature** `contract-debt` · **Opened** 2026-08-22 · **State** open
**Observed** Four occurrences, in two C2 artifacts, all found on 2026-08-22.

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

All four share one shape: a true statement about a moving system, written without
the date that made it true. Nothing distinguishes such a sentence from a live one,
and the cost is asymmetric — a stale *"it does not do X"* makes a heritage look
worse than it is, and a stale *"it does X"* makes it look better.

**Derivable** partly. The temporal markers that hide a date — *today*,
*currently*, *still*, *not yet*, *remains*, *for now* — are detectable by pattern.
Whether the sentence carrying one is stale is not.
**Qualification** `unknown`. STD-0100 v2.3 states the rule — an assertion about
the code carries its date and its commit — and, like the `type` → `domain` rule of
OS-004, it is enforced by nothing and holds by being applied. Whether the pattern
check is worth its false positives is the owner's call, and it was deliberately
not taken on 2026-08-22.

---

# Non-conforming instances

#### GOV-0002/OS-006 — `PRINCIPLES-REGISTRY.md` does not follow `<ID>-<Title>.md`

**Nature** `non-conforming` · **Opened** 2026-08-21 · **State** open
**Observed** It declares `id: FDN-PRINCIPLES` and its filename carries no
title, while STD-0102 mandates the pattern. Invisible to every pass until
2026-08-21.
**Derivable** yes — a check comparing filename to `id` and `title`
**Qualification** `unknown`. `FDN-PRINCIPLES` is itself outside the
`<PREFIX>-NNNN` form; renaming touches an identifier, which STD-0102 forbids
outside a declared exception.

#### GOV-0002/OS-007 — `ADR-0003-Selection-Engine.md` does not carry its full title

**Nature** `non-conforming` · **Opened** 2026-08-21 · **State** open
**Observed** Its declared title is *Selection Engine Strategy Delegation*.
The same check as OS-006 would find it.
**Derivable** yes
**Qualification** none required; a rename of the file, not of the identifier.

---

# Defects

#### GOV-0002/OS-009 — `sync_mirrors.sh` stops at the first failing mirror

**Nature** `defect` · **Opened** 2026-08-21 · **State** open
**Observed** On 2026-08-21 GitHub rate-limited the SPOT host and `set -e`
ended the run. Codeberg was reachable and was never published. One mirror is
not a dependency of another.
**Derivable** no
**Qualification** none required.

#### GOV-0002/OS-010 — `sync_mirrors.sh` pulls its own new version mid-run

**Nature** `defect` · **Opened** 2026-08-21 · **State** open
**Observed** The run that delivered the script's own improvement printed the
old message: bash had already read the old file. Harmless at this size; on a
larger file the shell can resume at a shifted byte offset.
**Derivable** no
**Qualification** none required.

#### GOV-0002/OS-016 — An evidence extract can omit the pattern that fired the rule

**Nature** `defect` · **Opened** 2026-08-22 · **State** partially mitigated
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
**Derivable** no
**Qualification** `unknown`. The mitigation moves the boundary, it does not
remove it: a verbose enough log will put a match beyond 200 again. The
complete answer is an extract centred on the match, and it requires the
finding to carry the position at which the signature matched — a field on
`RuntimeFinding` or on `LogEntry`, which is a contract change and was not
taken today.

#### GOV-0002/OS-018 — `aistack.funnel` has never been able to run

**Nature** `defect` · **Opened** 2026-08-22 · **State** open
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
**Derivable** yes — importing every module of the package and reporting the
failures is exactly what found it, and that is what OS-002 will do
continuously
**Qualification** `unknown`. Three readings, and only the owner can choose:
`core.py` exists somewhere outside this repository and should be brought in;
the module was abandoned and should be removed; or it is planned and its
absence should be declared. GOV-P-001 forbids the AI from writing the missing
module — an ASCII envelope with an integrity check is a specification nobody
has written down here.

---

# Published artifacts

#### GOV-0002/OS-011 — `aistack-core:0.1.0` carries bytecode the heritage does not know about

**Nature** `published` · **Opened** 2026-08-22 · **State** open
**Observed** Built 2026-08-19 under a `.dockerignore` whose `__pycache__` and
`*.pyc` patterns matched only the context root, so every
`src/aistack/**/__pycache__` entered the image. Corrected in the file on
2026-08-22 by `108b8a7`; the published image predates the correction and is
pinned by digest in `docker-compose.yml`.
**Derivable** no
**Qualification** `unknown` — rebuild and republish, or leave a one-shot
validator as it is and record why.

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
**Qualification** `unknown` — add authentication, or accept the exposure in
writing now that the surface is reduced.

---

# Decisions

#### GOV-0002/OS-013 — The ancestor's relation to the heritage is undecided

**Nature** `decision` · **Opened** 2026-08-21 · **State** open
**Observed** `/srv/aistack` is a git repository that contains the governed
one as a subdirectory. It holds the source of `aistack-backend:0.10`, built
2026-07-01, three days before this repository's first commit. Backed up
2026-08-22 to a private Gitea repository, `aistack-origin`. ADR-0009 decides
the migration of its function; it decides nothing about the repository
itself.
**Derivable** no
**Qualification** `unknown`. Both readings are defensible and lead to
opposite architectures: the ancestor is the product and this repository its
tooling, or the reverse.

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
**Qualification** `unknown`. Three readings, and they are not equivalent:
ship `docs/` in the wheel; make `--catalogue` mandatory and remove the
default; or state that an installed AIStack is a different subject from a
governed one and require the repository. The third is closest to FDN-P-004,
and the most inconvenient.

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
**Qualification** `unknown`. A declaration of expected state is governed
knowledge about a deployment, and GOV-P-001 forbids the AI from authoring it.
Whether it belongs in this repository at all is the prior question: it
describes one host, and this repository describes a product.

---

# Resolved

An entry moves here with the date and what discharged it, and is never
deleted. A register that erased what it had closed could not show that a
rule ever bound anything.

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
