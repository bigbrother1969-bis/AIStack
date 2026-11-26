---
artifact:
  id: ADR-0032
  title: Start-up checks
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 0.1
  status: Proposed
  owner: Architecture
  created: 2026-11-26
  updated: 2026-11-26

relations:
  references:
    - ADR-0011
    - ADR-0020
    - ADR-0025
    - ADR-0027
    - ADR-0028
    - ADR-0029
---

# ADR-0032 — Start-up checks

## Status

Proposed, 2026-11-26. Scope and choices decided with the owner the same day
(§ 1 to § 6). Slice B0 delivers this decision and the declaration
`boot_checks.yml`; nothing runs yet. The ADR stays Proposed until the first
slice that runs the checks is delivered.

## Context

*Read in the notes of the morning of 2026-11-26 (a building power cut at
02:06, the machines off at 02:17, back at about 02:23, then a second stop
by hand at 07:04) and in the code of the health strip, the restart watch
and the host collector.*

After every reboot the owner types the same controls by hand: the start
times of the boots, the failed units, the mounts, the containers (present,
running, stopped on purpose, unhealthy), the firewall chain, the port that
must answer, the backup that ran after the start, the snapshots, the UPS,
the monitor, and the same on the Raspberry. The result is always read the
same way: nothing red, then a line to say so. That reading belongs to the
program, and what changes from one start to the next (a power cut, a
stop by hand, a failed backup) is what an AI engine can help choose and
explain.

This builds on what exists:

- **The health strip** (the cartouche of the console) and its cockpit with
  the weighted score, the thresholds of OPS-0005 (disks), OPS-0006
  (backups) and OPS-0007.
- **The restart watch** (`ADR-0025`): it acts for 30 minutes after Docker
  starts and writes what it saw. The checks wait for it (§ 4).
- **The live badges** of the console (`/pending` and the script injected for
  signed-in sessions): the model for a value that must be live while the
  page itself stays static.
- **Privileged read-only scripts** (`ADR-0028` T3c, the exception of
  `ADR-0027` § 11) and **the host collector** (`ADR-0020`) which pushes the
  facts of the Raspberry into the data directory.
- **The AI-Engine Manager** (`ADR-0029`): callers by class, a call journal,
  the engines page.

## Decision

### 1. What the owner sees

- One **indicator per machine** (the MSI and the Raspberry; the Gigabyte,
  which switches itself off after its backups, is left out) in the health
  strip, beside the weighted score: *green* with the time since the last
  start while every control passes **now**; *orange* or *red* with the
  number of anomalies otherwise.
- A page of the detail: each control, its result, the time of its reading,
  and, for a start, the controls that failed and were resolved since
  (they leave the indicator, never the page).
- A single **Gotify summary** in the morning (08:00 by default), nothing for
  each finding. Urgent matters keep their own alerts (`ADR-0028`).

### 2. The time is the time since the start

The time shown is the one since the last reboot, read as *now minus the
uptime* of the machine, never from the journal's start line: the Raspberry
has no real-time clock and its journal dates a boot with the wrong clock.

### 3. Judge with code, explain with the AI

The verdict of each control is computed by deterministic code from facts
read on the machine. The AI engine does two things, both through the
AI-Engine Manager as a caller of the internal-only class:

1. **Choose** extra read-only controls from a **closed catalogue** declared
   by the program (database recovery in the logs, kernel disk errors, the
   reason of the last stop, the backup after the start, the Raspberry's
   state and clock, memory pressure), according to what the circumstances
   suggest (a power cut, a stop by hand, a failed unit). It never writes a
   command; it names catalogue entries, at most `max_extra_controls` of
   them. Without an engine, rules choose the same entries.
2. **Explain** the anomalies and suggest what to look at, in words. The
   facts it reads reach it as delimited, truncated data; whatever it
   answers is shown as text, never run, and never changes a verdict.

### 4. When to judge

The checks judge after `settle_minutes` (10 by default) from the start, so
the containers have time to come up and the restart watch has done its
window of work. Before that the indicator says that the start is being
checked.

### 5. How the facts are read

- **On the MSI**: a privileged script of closed read-only commands,
  `aistack-boot-facts`, in the pattern of `aistack-host-logs`, under the
  exception `ADR-0027` § 11 records for it (slice B1, 2026-11-26). Every five
  minutes it writes a file of **facts** (when the host started, from the
  uptime and never from the journal; the failed units; the mounted file
  systems; the containers with state and health; the rules of `DOCKER-USER`;
  the KVM modules; whether the previous run ended with a shutdown; the UPS;
  the status of the declared probes, under their label) and no verdict. A
  source that fails says so in the file, and the reader never takes it for a
  healthy host. It reads, it never acts.
- **On the Raspberry**: through the collector of `ADR-0020`, as another
  file pushed into the data directory; no SSH from AIStack.
- **The monitor** (Uptime Kuma) is read through an API key entered in
  Settings (decided 2026-11-26, slice B4b): one request on `/metrics`.

### 6. The declaration

What a healthy start is belongs to the owner and is declared in
`boot_checks.yml`, overridable in the configuration directory like every
declaration: the reference list of containers, the ones stopped on
purpose, the mounts, the number of rules of the DOCKER-USER chain, how
much each finding weighs (ignore, warning, critical), the options of the AI
and of the summary. An undeclared list is skipped, never guessed. The
shipped values are neutral. The indicator stays **outside** the weighted
health score unless the owner sets `indicator_weighted`.

## Consequences

- The morning controls cost the owner nothing and say the same thing every
  day; the AI is useful on the days that differ.
- The program can be replayed on a recorded morning: the facts of
  2026-11-26 become a regression test of the verdict.
- A privileged script is added to the MSI (read-only, closed commands), and
  one more file travels from the Raspberry.
- A control the owner did not declare is not run: a first start gives a
  shorter list, which the owner completes from the page.

### 7. The verdict and what a control may say

A control passes, waits (*pending*, before `settle_minutes` after the
start), is to watch, is to fix, is *skipped* (the owner declared nothing to
compare with) or *unknown* (its source did not answer). Only the last two
are never a pass. The overall status is the worst answer; pending is not an
anomaly. The previous run's end ("no shutdown": power loss or hard stop) is
information, never an anomaly. An incident, a control that failed after the
start, stays in the detail once resolved until the next start. With no
fresh facts the verdict is *unknown*, never green.

## Open points

1. The severities and the reference list shipped as examples, to be fixed
   with the first facts read.
2. How AIStack reads Uptime Kuma: decided 2026-11-26 by the owner, an API key (slice B4b).
3. Whether the absence of KVM modules is ever a finding (shipped: ignored).
4. Whether the indicator should weigh in the score after a period of use.

## Implementation state

| Slice | State |
|---|---|
| B0: this decision and the declaration `boot_checks.yml` with its loader | done, 2026-11-26 |
| B1: the facts of the MSI, read by a privileged script of closed commands (`aistack-boot-facts`, its unit and timer, the reader `boot_checks.facts`, the exception of `ADR-0027` § 11) | done, 2026-11-26 |
| B2: the base controls (units, mounts, containers, health, `DOCKER-USER`, probes, KVM, UPS, disks and backups read from the cockpit), the deterministic verdict, the incidents since the start, the Task `boot.check` run by the Runtime through `boot_check --once` and `--suggest`; Uptime Kuma and Timeshift not yet | done, 2026-11-26 |
| B3: the indicator in the health strip (a static label the signed-in page fills from `/boot-state`, the time since the start counted at each load, a verdict older than 40 minutes read as *not judged*), the page `/boot-check/`, the console card, a pass of the vigil, the manuals; no new writer | done, 2026-11-26 |
| B4: a companion machine through the collector: the same host unit writes its facts (plus the power and temperature flags and whether the clock is set) in its `boot` folder, the push brings them to the MSI, `boot.check` judges each in a verdict file of its own (reachable, failed units, declared mounts, throttled, clock), a pill and a part of the page per machine; no new writer | done, 2026-11-26 |
| B4b: Uptime Kuma read through an API key entered in Settings (`/metrics`, Basic, one request); a monitor down or missing from `expected_monitors` is `monitor_down`; a paused monitor is not published and counts as missing; no key means skipped; no new writer | done, 2026-11-26 |
| B5a: the extra controls without any AI: the circumstances computed from the facts (stop not clean, UPS event, recent restart, restart inside the backup window, memory under pressure), a closed catalogue of five read-only controls (database recovery, kernel disk errors, cause of the previous stop, backup after the restart, memory and swap) linked to circumstances by `boot_checks.yml`, chosen by a rule, capped by `ai.max_extra_controls`; new facts are counts and flags, never log lines; the verdict records the circumstances and the controls chosen; no new writer | done, 2026-11-26 |
| B5d: the morning of 26 November 2026 replayed as a test (`tests/unit/boot_checks/test_replay_26_november.py`): hard stop at 07:04:42, six of the eight declared databases recovered, no disk error; the controls of B5a must see the circumstances, name the six databases, stay pending in the first minutes, and the morning summary must tell the anomaly; the same morning with the base controls only stays green, which is what the catalogue corrects | done, 2026-11-26 |
| B5e: the sentences of the controls told in the owner's language: the controls keep writing them in English (stable text for the verdict file, the command and the engines), and `boot_checks.phrases.say` gives the catalog's version, with the numbers and names, on the page and in the morning message; a sentence that is not the program's own is shown as it is; the command stays in English | done, 2026-11-26 |
| B5b: the AI engine of the house chooses among the same catalogue: the caller `boot_checks` is `internal_only` in `ai_policy.yml`, the operation `choose` is of the kind `diagnosis`; the rules of B5a are a floor the engine cannot lower, it adds controls up to `ai.max_extra_controls` and says why in one sentence; every identifier is validated against the catalogue and an answer that is not the expected object is silence; asked once per start and set of circumstances (again after an hour when the rules decided for lack of an answer), the verdict of the rules being written first because a local engine may take minutes; the verdict records who chose and the sentence (`chosen_by`, `choice_reason`); the page says it | done, 2026-11-26 |
| B5c: the AI engine explains the anomalies: for each control to watch or to fix (at most three per pass) the operation `explain` of the kind `explanation` is asked through the same managed path and the `boot_checks` caller; the answer is text, cleaned and cut, kept in the verdict (`explanations`) with the control, its status and its sentence as they were when asked; shown on the page only, under the mention "the AI's explanation, not verified", never in the morning message, never executed, never changing a verdict; asked once while the control keeps the same status and sentence in the same start; the question is written first as an empty marker (retried after an hour) so a pass cut short or a silent engine is not asked again at every pass; one budget of 240 s is shared with B5b because the vigil stops a pass at 300 s | done, 2026-11-26 |
| O1b: disk health from Scrutiny (observability, 2026-11-26): the base control `disks` reads `/api/summary` then `/api/device/<wwn>/details` (address `AISTACK_SCRUTINY_URL` in Settings, no key); a disk is known by its WWN, an archived disk is not judged, `smart_support` is not used, a report older than `disk_report_hours` (36) or a disk without attributes is not read; findings `disk_failing` (SMART failure, critical) and `disk_attribute` (reallocated, spin-retry, reported-uncorrectable, pending or offline-uncorrectable raw value above zero, warning); Scrutiny's statistical statuses and the age (`disk_old_hours`, absent by default) are information only, and counters such as CRC errors wait for the history of slice O2 | done, 2026-11-26 |
| O1c: the machines Beszel watches (observability, 2026-11-26): the base control `systems` reuses the Beszel provider and the read-only account of the architecture page (no new secret; the address is the one of `infrastructure_topology.yml`); the reasons never carry the address or the account; findings `system_down` (a machine Beszel calls down) and `system_pressure` (disk or memory use at or above `system_disk_percent` / `system_memory_percent`, 90 by default, or temperature at or above `system_temperature_celsius`, 80), both warnings; a paused or pending machine and a missing value are not judged, a machine with no reading is not read; the CPU is not judged (one instant, left to the history of slice O2) | done, 2026-11-26 |
| B6: the morning Gotify summary: one message a day at `summary.at` (owner's time zone, the one of the security digest), read from the verdicts, one line per machine, the controls to watch and the incidents resolved since the start (three of each at most); rings only when a machine is critical; told once a day, tried again when Gotify does not answer; nothing without a verdict, the first pass of a fresh install only notes the day; no new writer (a day in the notification state) | done, 2026-11-26 |
