---
artifact:
  id: ADR-0031
  title: Attack recovery
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C1
  confidence: Declared
  version: 0.1
  status: Proposed
  owner: Architecture
  created: 2026-11-21
  updated: 2026-11-21

relations:
  references:
    - ADR-0011
    - ADR-0018
    - ADR-0020
    - ADR-0028
---

# ADR-0031 — Attack recovery

## Status

Proposed, 2026-11-21. Scope and seven choices decided with the owner the
same day (§ 1 to § 7). Nothing is built; this ADR stays Proposed until the
first slice is delivered.

## Context

*Read in the project notes of November 2026 and in `ADR-0028` and
`ADR-0018`; the weak points of § 7 are not yet checked on the machines.*

The owner asked for an alert when an attack happens (a ransomware, for
instance) and for a way back to an earlier version of the whole system that
was validated. This builds on what exists:

- **Detection, read-only.** `ADR-0028` (T1 to T4): exposure, drift of files
  and units, refused connections, who tried to get in, alerts through
  Gotify. It also decides a response ladder (§ 5), one automatic action
  under conditions (§ 6) and a purge-and-restore level that needs a
  snapshot, a verified clean point and the owner's confirmation (§ 7).
  None of the ladder is built.
- **Restoring in a sandbox.** `ADR-0018`: recipes that restore a service
  in a sandbox, a report and a measured time.
- **A history of what happened.** `ADR-0011`: the Time Machine keeps dated
  events and explanations, and a validation can be recorded in it.
- **The copies.** A nightly restic copy of the MSI to the vault host
  (append-only server), a weekly third copy to the Raspberry (append-only),
  a weekly ReaR image, the vault host switching itself off after half an
  hour without a connection.

An attack does not always come by the worst door, so the recovery is
decided by extent, not as one "whole system".

## Decision

### 1. Three extents, in this order

| Extent | What is hit | Way back |
|---|---|---|
| S2 | One service or one container | Restore that service in a sandbox, check it, put it back |
| S1 | Data (the shared folders, the databases) | Restore the data from a validated restic point |
| S3 | The whole machine | A written plan, kept off the machine: network boot of the ReaR image, the archive of a validated point, the data, new secrets, checks |

S2 is built first, then S1. S3 stays a plan on paper (§ 5): it is not
automated, and the orchestration cannot depend on the machine that was hit.

### 2. Alert and act: only what is reversible and bounded

The alert is the ladder's level 0 of `ADR-0028`. The only automatic actions
are the two reversible ones: closing the Internet entrance (level 1 of
`ADR-0028`, under its § 6) and putting the shared folders in **read-only**.
Both need two signals of different kinds, a fresh reading, a bounded effect
that reopens by itself, the owner told first, and a simulation period kept
on before the action is enabled (the conditions of `ADR-0028` § 6). Nothing
here purges, deletes or restores on its own: a restore is always the owner's
decision, confirmed word by word.

### 3. Where it runs

Detection runs on the MSI **and** on the Raspberry, which is the independent
witness already planned by `ADR-0028` § 4. The recovery plans and the
validations are kept off the MSI, on the Raspberry, and printed for S3.

### 4. What "validated" means

A recovery point is *validated* when its restoration in a sandbox succeeded
(`ADR-0018`) **and** the owner marked it. The validation is recorded in the
Time Machine (`ADR-0011`) and its copy is kept off the MSI. A point
validated more than 90 days ago is refused (the number to be fixed when the
first slice is built). The point chosen is the latest validated one that
precedes the first sign of compromise with a margin; a point newer than that
is refused (`ADR-0028` § 7).

### 5. Detection of an encryption

Reading only: five discreet canary files per shared folder, with ordinary
names, checked every five minutes; the rate of change of the files; and the
reading of the restic snapshots. A canary changed or missing, or an unusual
rate of change, is a finding for the vigil, urgent when it agrees with a
second signal of another kind. Detection acts on nothing by itself.

### 6. Objectives

A loss of data of up to 24 hours is tolerated (the nightly copy). For S3 the
aim is a recovery within a day; this is to be measured by playing it once,
since the network boot of the ReaR image has no recorded result yet.

### 7. Strengthen the copies before any code

No software replaces a copy that an intruder cannot touch. Before the
detection is built, the weak points below are checked by read-only
commands, and fixed in this order, beginning with the first:

1. The ReaR folder of the vault host is exported read-write to the MSI: an
   intruder on the MSI could erase or encrypt those archives. The way out:
   deposit with an account that can only add, or have the vault host pull
   the archive.
2. The restic passwords are on the MSI: append-only protects against
   erasing, not against reading.
3. How many nights the MSI's repository keeps decides how far back a late
   discovery can go.
4. Whether the Samba shares are writable from the Macs and the laptops: if
   they are, S1 is the realistic road.
5. Where AIStack's own Time Machine is saved: if only on the MSI, the
   validation of § 4 must leave the MSI.
6. The result of the network boot of the ReaR image: until a full restore
   has been played, S3 is a hypothesis.

## Consequences

- A first slice (the strengthening of § 7, then the reading of § 5) delivers
  value with no action at all.
- A false positive costs an alert, and at worst a closed entrance or
  read-only shares that reopen by themselves, never data.
- The Raspberry's availability matters more: it is the witness and holds the
  plans.
- AIStack does not claim to make the system safe: a copy infected before it
  was discovered remains possible; the margin and the sandbox restore reduce
  that risk without removing it, and no replay of a full recovery has been
  made yet.

## Implementation state

| Slice | State |
|---|---|
| R0: this decision | done, 2026-11-21 |
| § 7: the six weak points checked by read-only commands, then fixed one by one | not started |
| R1: detection of an encryption, reading only (canaries, rate of change, restic snapshots) feeding the vigil | not started |
| R2: validated recovery points: a page by extent, the latest point, its age, its last sandbox validation, a finding when none is recent enough; recorded in the Time Machine and copied off the MSI | not started |
| R3: the choice of the point before the first sign, with a margin; refusal of a newer one | not started |
| R4: the recovery plans S1, S2 and S3, word by word, with an offline copy on the Raspberry and the checks after recovery | not started |
| R5: the two reversible actions (read-only shares, closing the entrance) in simulation first, then the S2 recipe on the owner's confirmation | not started |
