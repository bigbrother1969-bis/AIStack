---
artifact:
  id: OPS-0004
  title: Sustainability Qualifications
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.5
  status: Draft
  owner: Operations
  created: 2026-09-04
  updated: 2026-09-11

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
- **Deployment misconfiguration** — named 2026-09-11, by the second
  reference incident below, filling the slot this entry left open since
  2026-09-04: a service deployed without the operational safeguards its
  own kind of workload requires — no log rotation, no size cap declared
  anywhere — such that ordinary operation degrades the host over time.
  Distinct from energy inefficiency and sustainability anomaly, which are
  about resource consumed *while running*; this one is about what was
  missing when the thing was set up.

## First reference incident — `aistack-selection-ui`'s `--reload`, qualified

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

## Second reference incident — GIGABYTE disk exhaustion, 2026-09-11, qualified

A second case, given directly by the owner 2026-09-11 in answer to what J7
(`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`, the health cockpit) needed a
storage domain for: on GIGABYTE, a service producing logs with no rotation
and no size cap filled the host's disk — *"des logs en folie qui ont
rempli le disque / je n'avais plus de place disponible"*.

Examined against the vocabulary, 2026-09-11, the owner found this case to
carry:

- **deployment misconfiguration** — yes: this is the case the first
  incident's entry above left the definition open for. No rotation, no
  cap, declared nowhere — the gap is in how the service was set up, not
  in one bad run;
- **technical debt** — no;
- **energy inefficiency** — no;
- **sustainability anomaly** — no.

One qualification, the only one the owner found this case to carry —
`deployment misconfiguration` is no longer an open slot.

## Third reference incident — power-outage restart loops, 2026-09-11, qualified

A third case, given directly by the owner 2026-09-11 in answer to what J7
(`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`, the health cockpit) needed a
Services domain for — the case itself, the owner's own words:

> *"Suite à une coupure électrique subite, des containers redémarraient en
> boucle ou restaient en unhealthy : problème visible sur la page homepage
> hébergée par le raspberry."*

(After a sudden power outage, containers were restart-looping or stuck
unhealthy — visible on the Homepage page hosted by the Raspberry.)

Examined against the vocabulary, 2026-09-11, the owner found this case to
carry:

- **technical debt** — yes;
- **sustainability anomaly** — yes;
- **deployment misconfiguration** — yes;
- **energy inefficiency** — no.

Three qualifications, one explicitly excluded by the owner rather than left
unconsidered — the same shape the first reference incident took, mirrored
here for a different case.

**Scope, declared alongside the qualifications.** Two further questions were
put to the owner before any code, per `ARC-P-006` (never build a
correlation from a single case without deciding its scope from the owner
first):

- **Detection scope** — whether to count restarts over time
  (`docker inspect`'s `RestartCount`) or read state at one instant only.
  The owner chose **instantaneous state only** for this first lot: a
  container flagged because it is *currently* restarting or declared
  unhealthy, never because it restarted N times over a window. Restart-loop
  counting stays out of scope, the same way storage's v1 left fill-rate
  detection out (`PLAN-J7` § 6.4).
- **Affected host(s)** — the incident was visible on the Raspberry's own
  Homepage page, and the owner confirmed **both hosts** were affected.
  AIStack's `DockerProvider` observes only the machine it runs on (`PLAN-J2`,
  `claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`, § *Une réduction de
  périmètre assumée`) — there is no Docker provider reaching the Raspberry
  remotely. GIGABYTE is instrumented with existing infrastructure; the
  Raspberry stays explicitly out of scope for this lot, a named absence
  (`FDN-0003` Article 12), not a silent one — see `PLAN-J7` § 8.3.

## Fourth reference case — Sauvegarde/PRA, 2026-09-11, qualified

A fourth case, given directly by the owner 2026-09-11 in answer to what J7
(`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`, the health cockpit) needed a
Sauvegarde/PRA domain for.

**Not an incident — a declared requirement, and that difference is recorded
here rather than smoothed over.** The first three reference cases each
describe something that already happened: a container caught permanently
reloading, a disk that actually filled, containers observed restart-looping
after a real power outage. This fourth case is different in kind: the owner
did not describe a past failure, but stated a standing requirement — the
owner's own words:

> *"Vérifier qu'il existe réellement une sauvegarde, qu'elle est
> fonctionnelle et que les backup ne sont pas trop vieux."*

(Verify that a backup really exists, that it is functional, and that
backups are not too old.)

`GOV-P-001` governs a stated requirement exactly as it governs a stated
incident: the owner states the knowledge, this register records what was
said, and invents nothing beyond it — a missing or stale backup was never
observed here the way GIGABYTE's disk exhaustion was; the requirement to
detect one, should it occur, is what the owner stated and what this case
qualifies.

Examined against the vocabulary, 2026-09-11, the owner found this case to
carry:

- **technical debt** — yes;
- **deployment misconfiguration** — yes;
- **energy inefficiency** — no;
- **sustainability anomaly** — no.

Two qualifications, two explicitly excluded by the owner rather than left
unconsidered — the same shape the first and third reference cases took,
mirrored here for a declared requirement rather than an incident.

**Scope, declared alongside the qualifications.** Several further questions
were put to the owner before any code, per `ARC-P-006` (never build a
correlation from a single case without deciding its scope from the owner
first):

- **Which backup** — the owner's stated requirement names no specific
  backup; the owner chose the WordPress backup written by
  `/srv/scripts/backup-wordpress.sh` to
  `/media/BACKUP/persiaut-consulting/wordpress/` as the v1 target — the one
  backup mechanism already running and already observable, not every backup
  the homelab might eventually have.
- **What "tests réguliers" and "procédures à jour" mean for v1** — the
  owner's stated requirement also named periodic restore tests that
  demonstrate the backup systems work, and documentation of procedures kept
  current. Both are **out of scope for this first lot**, the owner's own
  choice, mirroring storage's v1 leaving fill-rate detection out
  (`PLAN-J7` § 6.4): v1 checks only that a backup file exists and is not too
  old. Restore testing and documentation currency are named here as an
  absence this register records (`FDN-0003` Article 12), not a silent
  omission — revisited later against a real case, per `ARC-P-006`, not
  built speculatively now.
- **Host** — the WordPress backup script, and this domain's v1 scope, run
  on **GIGABYTE**. This needed asking directly: `OPS-0005`'s own
  `storage_thresholds.yml` already declares `/media/BACKUP` as a storage
  threshold only for the `raspberry` host, not GIGABYTE, so which host
  actually runs the backup script was not obvious from existing
  declarations and was confirmed by the owner rather than assumed.
- **Staleness threshold** — **7 jours**: the maximum age the newest backup
  file may reach before it is considered too old. `OPS-0006` (new)
  declares this value the same way `OPS-0005` declares storage thresholds.

## What this register does not do

**Updated 2026-09-11 (third time, for the fourth reference case)** — this
section has been corrected in place three times now, each time the state
it described stopped being current, rather than left to read as if it had
always been so.

As of `0.6.0` (`claude/PLAN-J5-EVALUATE-QUALIFIED-FINDING-2026-09-11.md`),
`energy inefficiency` and `sustainability anomaly` are wired into a runtime
finding: `aistack.runtime.evaluate` correlates `UnexplainedConsumption`
against `TemperatureReading` into a `RuntimeFinding` citing one or both.

As of `PLAN-J7` § 6 (storage domain), `deployment misconfiguration` is
additionally wired by `aistack.runtime.evaluate_storage`, citing a
`StorageShortage` already confirmed against `OPS-0005`'s declared
thresholds.

As of `PLAN-J7` § 8 (Services domain), `technical debt`,
`sustainability anomaly` and `deployment misconfiguration` are additionally
wired by `aistack.runtime.evaluate_services`, citing a `ContainerDistress`
already confirmed by `find_container_distress` — a container currently
restarting, or declared unhealthy, on the one host AIStack can observe
(GIGABYTE). `RuntimeFinding` carries a `qualifications` field
(`src/aistack/contracts/runtime_finding.py`) enforcing this register's
closed vocabulary throughout.

**`technical debt` is cited without a backlog register, and that is a
narrower claim than the one this section used to make.** The paragraph
removed here (until 2026-09-11) said the qualification needed "a backlog
register this heritage does not have yet, something a corrected issue can
be removed from" before it could be cited at all. That register still does
not exist, and nothing here builds one: `evaluate_services` cites
`technical debt` only because the owner examined this one real case
directly and said it applied (`GOV-P-001`) — the same per-case citation
`deployment misconfiguration` already received from the second reference
incident before any provider existed for it. A general "is this container's
condition tracked as a pending fix" register remains unbuilt; nothing here
depends on one.

As of `PLAN-J7` § 9 (Sauvegarde/PRA domain), `technical debt` and
`deployment misconfiguration` are additionally wired by
`aistack.runtime.evaluate_backup`, citing a `BackupGap` already confirmed
by `find_backup_gaps` — a backup location under `OPS-0006`'s declared
thresholds found to hold no backup file at all, or one older than the
declared threshold, on the one host and path the owner confirmed
(GIGABYTE, the WordPress backup).

Every one of `OPS-0004`'s four qualifications has now been cited by at
least one wired `RuntimeFinding` — `energy inefficiency` remains the only
one this register has never found a real case to carry.
