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
- **The monitor** (Uptime Kuma) is read through a way to be chosen in the
  slice that needs it (an API key or a status page).

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

## Open points

1. The severities and the reference list shipped as examples, to be fixed
   with the first facts read.
2. How AIStack reads Uptime Kuma (API key or status page).
3. Whether the absence of KVM modules is ever a finding (shipped: ignored).
4. Whether the indicator should weigh in the score after a period of use.

## Implementation state

| Slice | State |
|---|---|
| B0: this decision and the declaration `boot_checks.yml` with its loader | done, 2026-11-26 |
| B1: the facts of the MSI, read by a privileged script of closed commands (`aistack-boot-facts`, its unit and timer, the reader `boot_checks.facts`, the exception of `ADR-0027` § 11) | done, 2026-11-26 |
| B2: the base controls, the verdict, `boot_check --once` | not started |
| B3: the indicator in the health strip, the detail page, the console card, the manuals | not started |
| B4: the Raspberry through the collector | not started |
| B5: the AI choice in the closed catalogue and the explanations | not started |
| B6: the morning Gotify summary | not started |
