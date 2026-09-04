---
artifact:
  id: OPS-0004
  title: Sustainability Qualifications
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.1
  status: Draft
  owner: Operations
  created: 2026-09-04
  updated: 2026-09-04

relations:
  references:
    - STD-0300
    - FDN-0012
    - FDN-0002
---

# OPS-0004 — Sustainability Qualifications

## Purpose

This register declares what each of VS-4's four qualifications — technical
debt, deployment misconfiguration, energy inefficiency, sustainability
anomaly — means, in the owner's own words, so a runtime finding can cite
one or more of them instead of inventing a severity label. `STD-0300` §
VS-4 criterion 4.5 requires each qualification a finding carries to be
traceable to a distinct policy; this is that policy for the vocabulary as
a whole.

## Provenance

Every definition below is the owner's own statement, given directly,
2026-09-04, in answer to a question asking why the reference incident
(`aistack-selection-ui`'s permanent `--reload`, documented in `STD-0300` §
VS-4) deserved each qualification. `GOV-P-001` governs this register the
same way it governs `OPS-0001` and `OPS-0003`: the owner states the
knowledge, the system records what was said, and invents nothing beyond
it.

## The vocabulary is closed

Four qualifications, and no more may be added without the owner naming a
fifth: technical debt, deployment misconfiguration, energy inefficiency,
sustainability anomaly. A finding does not need to carry all four —
`STD-0300` § VS-4 criterion 4.5 was reworded on 2026-09-04 for exactly
this reason: the reference incident, examined against all four, was
found by the owner to carry three of them, not four (below). What makes
a finding derived knowledge rather than an opinion about severity is that
whichever qualifications it does carry are each cited to this register —
not that a fixed count of them is always reached.

## What each qualification means

- **Technical debt** — applies while the issue is known and pending
  correction; it is a standing entry on a backlog of fixes still to make.
  The qualification is not permanent: once the correction lands, the
  label no longer applies going forward — the record of it having
  applied stays in history (a validation suite entry, a commit, a
  document), but nothing continues to hold the corrected system as
  carrying that debt today.
- **Energy inefficiency** — resource (CPU, in the reference incident)
  consumed for no functional benefit — no work is being done that the
  consumption produces.
- **Sustainability anomaly** — excessive resource consumption with a
  physical consequence: heat generated, and a risk to the hardware
  components running it. Distinct from energy inefficiency, which is
  about the waste itself; this is about what the waste does to the
  machine.
- **Deployment misconfiguration** — not yet defined. The owner's own
  reading of the reference incident found this qualification not
  pertinent to that case (below); its definition is left open until a
  real case names what it means, per `GOV-P-001` and `ARC-P-006` — the
  same discipline that kept `OPS-0001`'s `S-001`–`S-003` groundings
  `unknown` and `KNOWN_DEVELOPMENT_FLAGS` to one entry.

## The reference incident, qualified

Examined against the vocabulary above, 2026-09-04, the owner found
`aistack-selection-ui`'s permanent `--reload` (`STD-0300` § VS-4's
reference incident) to carry:

- **technical debt** — yes, while it was outstanding on the corrections
  backlog; not anymore, since it was fixed;
- **energy inefficiency** — yes, 48–58 % of one CPU core consumed for no
  functional benefit;
- **sustainability anomaly** — yes, excessive CPU consumption, excessive
  heat, a risk to the hardware;
- **deployment misconfiguration** — no, not pertinent to this case.

Three qualifications, one explicitly excluded by the owner rather than
left unconsidered — the exclusion is itself the fact this register
records, not a gap.

## What this register does not do

It does not wire any of the four qualifications into a runtime finding.
`RuntimeFinding` carries no qualification field today, and no code reads
this register — `STD-0300` § VS-4 4.5 records the criterion as advanced,
not satisfied. Some of the evidence each qualification needs now exists,
piece by piece, and each piece is named here precisely because a piece
existing is not the same as a finding carrying the qualification it
would support:

- **technical debt** — needs a backlog register this heritage does not
  have yet, something a corrected issue can be removed from. Not built:
  the owner declined to build one ahead of a real pending correction to
  seed it with, 2026-09-04.
- **energy inefficiency** — needs the "no functional benefit" evidence
  the reference incident had: no incoming requests, no active session.
  `aistack.runtime.activity_evidence.no_incoming_requests` reads the
  first half, from a log window already collected. "No active browser
  session" is not checked by anything.
- **sustainability anomaly** — needs a real temperature reading
  correlated to a CPU reading. `HostProvider.collect_temperatures`
  (`src/aistack/providers/host/provider.py`) reads `sensors` — the same
  source the owner's own Uptime Kuma temperature check reads — into
  `TemperatureReading`, which compares itself against the sensor chip's
  *own* declared "high"/"crit" limits rather than a threshold `aistack`
  proposed. Nothing correlates one of these against a `ContainerCpuReading`
  yet; the two readings exist, independently, with no function that
  reads them together.

Three separate providers, three separate pieces of evidence, and no
finding built from any of them — building the correlation itself from
one case (the reference incident, the one machine this has ever been
measured on) would be exactly what `ARC-P-006` warns against.

It does not define "deployment misconfiguration". A finding that is one,
when a real case names it, gets its definition the same way `frigate`'s
`intermittent` lifecycle got recorded in `OPS-0003` — stated once, by the
owner, about a real case, not guessed at in general.
