---
artifact:
  id: OPS-0003
  title: Container Lifecycle Declarations
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Operations
  created: 2026-09-04
  updated: 2026-09-04

relations:
  references:
    - OPS-0001
    - ADR-0009
    - FDN-0002
    - STD-0300
---

# OPS-0003 — Container Lifecycle Declarations

## Purpose

This register declares which containers the owner stops and starts on
purpose, and why — so that a running-state observation and a log finding
about that container can be read against what the owner actually intends,
rather than against a silent assumption that every container is expected to
run continuously.

`OPS-0001` names the gap this closes without being able to close it:

> A deeper gap has no field. The heritage cannot tell "stopped because
> broken" from "stopped on purpose", because nothing declares which
> containers are expected to run. `applies_to` treats the symptom; the
> knowledge that `frigate` is deliberately idle exists in one person's head.

This register is the field. FDN-0002 defines a *Knowledge Policy* as "a
governed rule defining how knowledge is evaluated, qualified or
interpreted", explicit and versioned — a lifecycle declaration is exactly
that, applied to one specific fact instead of a general one: not "how logs
are read" but "what this one container's absence means".

## Provenance

Every declaration below is the owner's own statement, given directly,
2026-09-04, in answer to a question about why `OPS-0001/S-004` fired on
`frigate` on 2026-08-22 with an empty remediation. `GOV-P-001` governs this
register the same way it governs `OPS-0001`: the owner states operational
knowledge, the system records what was said, and invents nothing beyond it.

**This is why the register holds exactly one declaration.** `OPS-0001`'s
gap is general — nothing here says every other container defaults to
`continuous`, or that `frigate` is representative of anything beyond
itself. A container with no declaration here is unasserted, not assumed;
`LifecycleRegister.for_container` returns `None` for it, and nothing reads
`None` as `continuous`.

## What `expected` means

Two values only, per declaration:

- `continuous` — the owner expects this container to run without the
  owner's own intervention; its absence is a candidate fault.
- `intermittent` — the owner starts and stops this container by their own
  choice, for their own reasons; its absence may be exactly that choice.

Neither value is inferred from a running-state history. `FDN-0003` Article
12 governs the alternative already rejected: a pattern the system noticed
on its own would be a psychological profile of the owner's habits dressed
as a fact, and the undeclared stays declared as such rather than replaced
by a plausible guess.

## How this changes a finding

`RuntimeFinding` and `Signature` are unchanged, and so is `OPS-0001`
itself — a signature's own `grounding` stays exactly what it was, because
the general remediation each one presupposes is still ungrounded for the
general case. `src/aistack/runtime/grounding.py::ground_findings` reads
this register *after* `qualify()` has run, and where a finding's subject
carries a declaration here, it adds that context to the finding: the
container, that it is declared `intermittent`, and the owner's own reason,
alongside — never instead of — the signature's original interpretation and
remediation. The finding's `grounding` field then cites this register by
identifier rather than reading `unknown`.

Nothing is suppressed. `frigate` stopping on purpose does not prove every
future finding about `frigate` is that same shutdown transition, so the
original remediation survives verbatim: what changes is that whoever reads
the finding sees the owner's own context before spending it.

## The declarations

```lifecycle
artifact: OPS-0003

declarations:

  - container: frigate
    expected: intermittent
    reason: >-
      The owner stops it most of the time because it consumes more
      resources than he needs running permanently, and starts it back up
      when he wants it. Its own backend going away on that stop is what
      OPS-0001/S-004 was reading on 2026-08-22, not a dependency fault.
```

## What this register does not do

It does not classify frigate's stop as a fault, a non-fault, or anything
else — that judgment stays with whoever reads a grounded finding.
Suppressing the finding instead would be a judgment this register does not
have the standing to make on the owner's behalf every time, and `STD-0300`
§ VS-4 criterion 4.9 already forbids a finding with no evidence; nothing
here trades that for a finding with no chance to be read.

It does not ground `OPS-0001/S-001`, `S-002` or `S-003`. Those remain
`grounding: unknown`, because no fact given so far speaks to what makes
their remediations the right ones — a VPN credential's declared location,
or a declared dependency between two services. Extending this register to
another container, or writing the register those three still need, happens
when the owner states the fact it would record, per `GOV-P-001`, not
before.
