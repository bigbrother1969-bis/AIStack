---
artifact:
  id: OPS-0004
  title: Sustainability Qualifications
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.8
  status: Draft
  owner: Operations
  created: 2026-09-04
  updated: 2026-10-05

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

**Detection scope widened, 2026-10-02 — restart loops counted over time.**
The instantaneous-only v1 missed a real loop for three weeks:
`arrstack/mularr` died at startup every ~17 seconds (its SQLite database
on NFS, 1,537 restarts), and read `running` at every instant the Cockpit
looked, between two crashes. The docker-events collector (`ADR-0011` § 20)
had recorded every `die` all along. The owner's choice, from three options
examined (recent restarts from that history, Docker's cumulative
`RestartCount`, or both): **count `die` events per subject over the last
60 minutes, threshold 5** (`aistack.runtime.restart_loop`,
`RestartLoop`). Same incident, same signature, same three
qualifications — the Services domain now cites both checks, instantaneous
and over time. Still GIGABYTE only, for the same reason as above.

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

## Fifth reference case — GPU, 2026-09-11, qualified

A fifth case, given directly by the owner 2026-09-11 in answer to what J7
(`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`, the health cockpit) needed a
GPU domain for.

**Not an incident — a declared requirement, the same distinction the fourth
reference case recorded rather than smoothed over.** The owner's own words:

> *"Vérifier que tous les services qui peuvent déléguer du calcul au GPU le
> font bien et surveiller la consommation du duo CPU/GPU."*

(Verify that all services able to delegate compute to the GPU actually do
so, and monitor the CPU/GPU duo's consumption.)

`GOV-P-001` governs a stated requirement exactly as it governs a stated
incident: the owner states the knowledge, this register records what was
said, and invents nothing beyond it — no GPU anomaly was ever observed here
the way GIGABYTE's disk exhaustion was; the requirement to detect one,
should it occur, is what the owner stated and what this case qualifies.

Examined against the vocabulary, 2026-09-11, the owner found this case to
carry:

- **technical debt** — yes;
- **energy inefficiency** — yes;
- **sustainability anomaly** — yes;
- **deployment misconfiguration** — yes.

**All four qualifications, none excluded — the first reference case to
carry the complete vocabulary.** Every prior case (below and above) found
the owner excluding at least one qualification as not pertinent; this one
is examined the same way and simply found to carry all four.

**Scope, declared alongside the qualifications.** Several further questions
were put to the owner before any code, per `ARC-P-006` (never build a
correlation from a single case without deciding its scope from the owner
first):

- **Host and hardware** — the owner confirmed **GIGABYTE**, an **NVIDIA
  Quadro P400** (2048 MiB VRAM). Confirmed live via `nvidia-smi`,
  2026-09-11: 1 % utilization, 142 MiB used, 49 °C at the moment of
  reading — an idle desktop GPU (Xorg, TeamViewer), no AI workload running.
  `power.draw`/`power.limit` both read `[N/A]` on this card — this GPU does
  not expose a power sensor via `nvidia-smi`, so power is out of scope by
  construction, not by choice.
- **Candidate services for delegation** — Jellyfin (transcoding), Immich
  (ML: facial recognition, object detection), Frigate (object detection) —
  the services the owner named as able to delegate compute to the GPU.
- **v1 scope: consumption monitoring only, not delegation verification** —
  the owner's own stated requirement names two things: verifying that
  services delegate correctly, and monitoring CPU/GPU consumption. Put to
  the owner directly, given the two need different detection mechanisms
  (Jellyfin's own delegation state is only observable via its live
  `/Sessions` API, during an active transcode; Immich's and Frigate's are
  declared in their own configuration, not read live) — the owner chose
  **consumption monitoring only** for this first lot, mirroring every prior
  domain's own v1 scope reduction (storage's static threshold over
  fill-rate detection, `PLAN-J7` § 6.4; backup's existence-and-freshness
  over restore testing, `OPS-0006` § *Out of scope*). Per-service
  delegation verification is named here as an absence this register
  records (`FDN-0003` Article 12), not a silent omission — revisited later
  against a real case, per `ARC-P-006`, not built speculatively now.
- **Declared thresholds** — three, declared against the live `nvidia-smi`
  reading above: temperature **80 °C**, sustained utilization **90 %**,
  memory occupancy **90 %**. Consigned in **`OPS-0007-GPU-Consumption-
  Thresholds.md`** (new registry, mirror `OPS-0005`/`OPS-0006`).

## Sixth reference case — État persistant, 2026-09-30, qualified

A sixth case, given by the roadmap's own revue de conception (R9,
`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md`, validated by the owner in full
2026-09-27) and examined against `OPS-0004`'s vocabulary directly with the
owner, 2026-09-30, for 1.6 tranche 2's own cadrage.

**Not an incident — a declared requirement, the same distinction the
fourth and fifth reference cases recorded rather than smoothed over.** R9's
own text: "Services avec état confrontés aux sauvegardes connues ; constat
« état persistant non couvert » avec stratégie par moteur... Pas de
généralisation au-delà (`ARC-P-006`)." No missing backup for a stateful
service was observed as an incident here the way GIGABYTE's disk
exhaustion was — the requirement to detect one is what the roadmap named
and what this case qualifies.

Examined against the vocabulary, 2026-09-30, the owner found this case to
carry:

- **technical debt** — yes;
- **deployment misconfiguration** — yes;
- **energy inefficiency** — yes;
- **sustainability anomaly** — yes.

**All four qualifications, none excluded — the second reference case,
after GPU, to carry the complete vocabulary.** Put to the owner directly
alongside the closest prior case (Sauvegarde/PRA, which carries only the
first two) rather than assumed to match it, and found to carry all four
instead.

**Scope, declared alongside the qualifications.** Three further questions
were put to the owner before any code, per `ARC-P-006`:

- **Which services** — the owner chose **"le stock déjà réel"**: the
  services already named in this session's own real PRA history
  (`OPS-0009`'s `pra_tests.yml`), not the ~60 services
  `service_categorization.yml` lists, most of which have never had a
  backup mechanism cited for them at all.
- **Mechanism** — a **new dedicated file**, `backup_strategy.yml`
  (`OPS-0010`), the same "declared, never guessed" convention
  `pra_tests.yml`/`backup_thresholds.yml` already hold.
- **Exposure** — a **sixth cockpit domain**, "État persistant" — the
  domain vocabulary (`OPS-0008`) reopened again, the same deliberate
  reopening `Tests PRA` already went through 2026-09-23. Weighted **25
  points**, the owner's own choice, same criterion as `Tests PRA` ("même
  ordre de grandeur que le domaine le plus proche en signification").

Full detail — the three real engines declared, the twelve services in
scope, and the three real gaps this session could not ground further
(Nextcloud, Immich, GIGABYTE's own host-level state) — is in `OPS-0010`.

## Seventh reference case — Écarts d'inventaire, 2026-09-30, qualified

A seventh case, given by the roadmap's own revue de conception (R9,
`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md`, validated by the owner in full
2026-09-27) and examined against `OPS-0004`'s vocabulary directly with the
owner, 2026-09-30, for 1.6 tranche 3's own cadrage — R9's remaining
bullet after tranche 2 (État persistant) closed its first.

**Not an incident — a declared requirement, the same distinction the
fourth, fifth and sixth reference cases recorded rather than smoothed
over.** R9's own text: "Écarts d'inventaire → quai → validation →
inventaire déclaré ; le CIDR reste une décision du owner." No real
inventory mismatch was observed as an incident here the way GIGABYTE's
disk exhaustion was — the requirement to detect one is what the roadmap
named and what this case qualifies.

Examined against the vocabulary, 2026-09-30, the owner found this case to
carry:

- **technical debt** — yes;
- **deployment misconfiguration** — yes;
- **energy inefficiency** — yes;
- **sustainability anomaly** — yes.

**All four qualifications, none excluded — the third reference case,
after GPU and État persistant, to carry the complete vocabulary.** Put to
the owner directly alongside the closest prior case (Sauvegarde/PRA,
which carries only the first two) rather than assumed to match it, and
found to carry all four instead.

**Scope, declared alongside the qualifications.** Four further questions
were put to the owner before any code, per `ARC-P-006`:

- **Which declared inventory** — the owner chose
  **`service_categorization.yml` alone**, not also `pra_tests.yml`: the
  only declared inventory with a `container` field alignable to what
  discovery actually observes. `cmdb_probe_targets.yml` (HTTP-probed
  URLs) has no equivalent on the discovery side at all.
- **Mechanism** — a **new dedicated runtime module**
  (`aistack.runtime.inventory_gap`/`evaluate_inventory_gap`), not an
  extension of `aistack.package_manager` — `ARCH-0013`'s own four Open
  Points (exact `PackageManager` interfaces, validation policies,
  integration conflict resolution, package version lifecycle) stay
  untouched.
- **Exposure** — a **seventh cockpit domain**, "Écarts d'inventaire" —
  the domain vocabulary (`OPS-0008`) reopened again, the same deliberate
  reopening `Tests PRA`/`État persistant` already went through. Weighted
  **25 points**, the owner's own choice, same criterion ("même ordre de
  grandeur que le domaine le plus proche en signification").
- **Directions** — **les deux sens**: a container discovered but
  declared nowhere, and a declared container never found running,
  neither locally nor via the last network discovery.

Full detail — the two sources joined, the two gap kinds, and what stays
explicitly out of scope (`pra_tests.yml`, `cmdb_probe_targets.yml`,
extending `aistack.package_manager`, widening the declared CIDR) — is in
`OPS-0011`.

## Eighth reference case — Tests PRA, service non déclaré, 2026-09-30, qualified

An eighth case, the roadmap's own last remaining bullet under its own R9
constat (`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md`, 1.6 tranche 4), examined
against `OPS-0004`'s vocabulary directly with the owner, 2026-09-30.

**Not an incident — a declared requirement, the same distinction the
fourth through seventh reference cases recorded.** R9's own text: "Liste
des services de `pra_tests.yml` proposée depuis la découverte ; résultats
seulement issus de vrais tests." No service was found untested as an
incident here — the requirement to detect one, before it is even declared
for testing, is what this case qualifies.

**Not a new reference case in a new domain — a fourth reason inside the
existing `Tests PRA` domain**, the owner's own choice at cadrage
(2026-09-30): a service `OPS-0010`'s own file (`backup_strategy.yml`)
already declares stateful, but `OPS-0009`'s own file (`pra_tests.yml`)
does not declare at all — one step further upstream than the domain's
existing `UNTESTED` reason, which already requires a `services:` entry
to exist.

Examined against the vocabulary, 2026-09-30, the owner found this case to
carry the same three qualifications the domain's first three reasons
already cite:

- **technical debt** — yes;
- **sustainability anomaly** — yes;
- **deployment misconfiguration** — yes;
- **energy inefficiency** — excluded, the same exclusion the domain's
  first three reasons already hold, not re-derived for this reason alone.

**Scope, declared alongside the qualifications.** Four questions were put
to the owner before any code, per `ARC-P-006`:

- **Source of the periphery** — the owner chose **`backup_strategy.yml`
  (`has_state: true`)**, not `service_categorization.yml`: the latter
  carries no statefulness signal at all, while the former already
  instruments exactly the distinction this case needs (`OPS-0010`).
- **Direction** — **one sense only**: a stateful service missing from
  `pra_tests.yml`. The reverse (a `pra_tests.yml` entry with no
  `has_state: true` counterpart) is never checked — `gigabyte`/`raspberry`
  are host-level entries tested by imaging, not services, and would be
  false positives under a two-sense check.
- **Exposure** — a **fourth reason inside the existing `Tests PRA`
  domain**, not an eighth cockpit domain: no change to
  `health_score_weights.yml`, no new `OPS-0004` weight decision.
- **Mechanism** — **calculated at render time**, the same discipline
  `OPS-0011` already holds: no new file, no new CLI command. The finding's
  own text states what to add (`name` + `last_test: null`); the owner
  edits `pra_tests.yml` by hand.

Full detail — the two declared sources joined, the fourth reason's own
shape, and the "never a fabricated `last_test`" guarantee (the roadmap's
own words, "résultats seulement issus de vrais tests") — is in
`aistack.contracts.pra_test_gap`/`aistack.runtime.pra_test_gap`'s own
docstrings; unlike the sixth and seventh reference cases, this one adds no
new governance register of its own, reusing `OPS-0009`/`OPS-0010` as
already declared.

## Ninth reference case — code en quarantaine, 2026-10-05, qualified

A ninth case, given by the owner on 2026-10-05 while deciding how to clean
AIStack of the code its first weeks left behind: "c'est aussi de la
gouvernance de gérer le code mort et obsolète. Ça rentre dans la dette
technique".

**Not an incident and not a domain of the host.** The code concerned is
AIStack's own: files found unused, put in quarantine for six weeks before
being deleted (`OPS-0012`). Nothing on the host misbehaves because of them.

Qualified by the owner's own words:

- **technical debt** — yes, named by the owner;
- **deployment misconfiguration**, **energy inefficiency**,
  **sustainability anomaly** — not named, and not applied: dead code costs
  nothing at run time and configures no deployment.

**Exposure — the "Dette technique" card, not an eighth cockpit domain.**
The seven domains `OPS-0008` weighs describe the host; the quarantine is
counted beside them as one more group of findings, so it costs the card
its weight once (`OPS-0008` § *Technical debt score*), and is listed in the
card by its own line. No change to `health_score_weights.yml`.

**One finding per quarantined item, whatever its state** — watched, used,
or ready to be deleted: the debt lasts until the deletion, and the card
clears when the register is empty. Full detail is in `OPS-0012`.

## What this register does not do

**Updated 2026-09-11 (fourth time, for the fifth reference case)** — this
section has been corrected in place four times now, each time the state
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

As of `PLAN-J7` § 10 (GPU domain), all four qualifications —
`technical debt`, `energy inefficiency`, `sustainability anomaly` and
`deployment misconfiguration` — are additionally wired together by
`aistack.runtime.evaluate_gpu`, citing a `GpuAnomaly` already confirmed by
`find_gpu_anomalies` — a GPU reading under `OPS-0007`'s declared
thresholds found to cross temperature, utilization or memory occupancy, on
the one host and card the owner confirmed (GIGABYTE, the Quadro P400).
This is the first domain-specific evaluator to cite `energy inefficiency`
— previously cited only by the original `aistack.runtime.evaluate`
correlation (CPU consumption against temperature), not by a domain
evaluator built for a `PLAN-J7` reference case.

As of 1.6 tranche 2 (État persistant domain, `OPS-0010`, 2026-09-30), all
four qualifications are additionally wired together a second time by
`aistack.runtime.evaluate_uncovered_state`, citing an `UncoveredStateGap`
already confirmed by `find_uncovered_state` — a declared stateful service
under `OPS-0010`'s own record found to name no known backup engine, on the
twelve services the owner confirmed ("le stock déjà réel").

As of 1.6 tranche 3 (Écarts d'inventaire domain, `OPS-0011`, 2026-09-30),
all four qualifications are additionally wired together a third time by
`aistack.runtime.evaluate_inventory_gap`, citing an `InventoryGap` already
confirmed by `find_inventory_gaps` — a container declared in
`service_categorization.yml` and never found running, or found running
and declared nowhere, joined against `OPS-0011`'s own two sources (the
local Docker catalog, and the last network discovery).

As of 1.6 tranche 4 (Tests PRA domain, fourth reason, 2026-09-30), the
same three qualifications the domain's first three reasons already cite
(technical debt, sustainability anomaly, deployment misconfiguration) are
cited a further time by `aistack.runtime.evaluate_pra_tests`, for a
`PraTestGap` citing `NOT_DECLARED` — a service `OPS-0010`'s own file
declares stateful but `OPS-0009`'s own file does not name at all, found
by `find_undeclared_pra_tests`, joining `backup_strategy.yml`'s declared
services against `pra_tests.yml`'s own.

As of 2026-10-05 (`OPS-0012`), `technical debt` alone is additionally
cited by `aistack.runtime.evaluate_quarantine`, for every item of the
quarantine register — dead code waiting for its deletion — counted in the
"Dette technique" card beside the domains rather than as one of them.

Every one of `OPS-0004`'s four qualifications is now cited by multiple
wired `RuntimeFinding` producers, across nine reference cases — the
vocabulary's coverage is no longer a gap this section needs to track.
