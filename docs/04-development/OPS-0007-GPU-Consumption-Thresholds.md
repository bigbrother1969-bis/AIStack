---
artifact:
  id: OPS-0007
  title: GPU Consumption Thresholds
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Operations
  created: 2026-09-11
  updated: 2026-09-11

relations:
  references:
    - OPS-0004
---

# OPS-0007 — GPU Consumption Thresholds

## Purpose

This register declares the GPU-consumption thresholds a `GpuReading` is
compared against before a `RuntimeFinding` cites `OPS-0004`'s four
qualifications — `technical debt`, `energy inefficiency`, `sustainability
anomaly`, `deployment misconfiguration` — for a GPU whose temperature,
utilization or memory occupancy has crossed a declared value. `STD-0300` §
VS-4 criterion 4.5 requires each qualification a finding carries to be
traceable to a distinct policy; this is that policy for GPU consumption,
the same way `OPS-0005` is the policy for storage capacity and `OPS-0006`
for backup freshness. No threshold here was chosen by AIStack — it is the
owner's own declared value, the same discipline `GOV-P-001` requires.

## Provenance

Declared directly by the owner, 2026-09-11, in answer to what `PLAN-J7`'s
fifth domain (GPU) needed thresholds for. Like `OPS-0006`, this register's
own case is a stated requirement rather than an observed incident — see
`OPS-0004` § *Fifth reference case* for that distinction, recorded there
rather than smoothed over. Unlike `OPS-0006`, whose thresholds needed no
live measurement to declare a sensible number (a backup either exists
recently or it does not), these three thresholds were declared against
real `nvidia-smi` output taken live on GIGABYTE, 2026-09-11 — the same
"declared against a real baseline" discipline `OPS-0005` holds against
`df -h`:

```
GPU: Quadro P400
utilization.gpu:    0 %
utilization.memory: 0 %
memory.used:         142 MiB
memory.total:       2048 MiB
temperature.gpu:      49 °C
power.draw:          N/A
power.limit:         N/A
```

`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` records the exchange that
produced each value.

## Why three kinds of threshold, and no power threshold

A GPU reading has several independent dimensions worth alerting on, unlike
a backup (one question: how old) or an OS volume (one question: how much
free space). Three are declared: **temperature** (a physical limit, °C),
**sustained utilization** (a workload signal, %), **memory occupancy** (a
capacity signal, %) — the same "% occupied" shape `OPS-0005`'s media-volume
thresholds already use, applied to VRAM instead of disk.

**No power threshold.** `nvidia-smi --query-gpu=power.draw,power.limit`
returns `[N/A]` for both fields on the owner's own card (a Quadro P400,
confirmed live 2026-09-11) — this GPU does not expose a power sensor
through `nvidia-smi` at all. A threshold this register could never compare
a real reading against would not be a declared absence (`FDN-0003` Article
12); it would be a number invented against hardware that cannot report it.
Power monitoring is out of scope by construction, not by the owner's
choice — a card that does report it would reopen the question, not this
register on its own.

## Declared thresholds

### GIGABYTE — Quadro P400

- **Temperature**: alert at or above **80 °C**. Current reading: 49 °C
  idle.
- **Utilization**: alert at or above **90 %** sustained. Current reading:
  0-1 % idle.
- **Memory occupancy**: alert at or above **90 %** of 2048 MiB. Current
  reading: 142 MiB (~7 %).

This is the only GPU declared so far — the one card the owner confirmed
exploitable, on the one host that has it, the owner's own choice for the
v1 scope of this domain (`OPS-0004` § *Fifth reference case*).

**No per-card key.** `GpuThreshold` (unlike `StorageThreshold`'s `mount` or
`BackupThreshold`'s `path`) names no card of its own: the owner's v1 scope
is one GPU per host, so every declared threshold applies to every
`GpuReading` a host produces. A second GPU on the same host, should one
ever be added, would need this register — and `GpuThreshold` itself — to
be revisited, per `ARC-P-006`, not assumed to work correctly today.

### Out of scope for this version

- **Per-service delegation verification** — confirming that Jellyfin,
  Immich and Frigate (the services the owner named as candidates) are
  actually delegating their compute to the GPU rather than the CPU. Named
  directly in the owner's own stated requirement ("vérifier que tous les
  services qui peuvent déléguer du calcul au GPU le font bien"), and
  explicitly deferred: this register and everything reading it check only
  consumption, never which process produced it or whether that process
  chose hardware acceleration. `OPS-0004` § *Fifth reference case* records
  why: Jellyfin's own delegation state is observable only during an active
  transcode session (its `/Sessions` API), while Immich's and Frigate's are
  declared in their own configuration rather than read live — two
  different detection mechanisms this first lot does not build.
- **Power draw** — see § *Why three kinds of threshold, and no power
  threshold* above; out of scope by construction, not by choice.
- **Any GPU other than GIGABYTE's Quadro P400** — no other host has been
  confirmed to carry an exploitable GPU; adding one happens when the owner
  names a real case for it, per `ARC-P-006`, not by extrapolating from this
  one.

Both scope reductions are a named absence this register records
(`FDN-0003` Article 12), not a silent one — mirroring `OPS-0005`'s and
`OPS-0006`'s own "out of scope for this version" sections, and revisited
later against a real case rather than built speculatively now.

## What this register does not do

It does not itself verify that any service is correctly configured to use
the GPU — only whether the GPU's own temperature, utilization or memory
occupancy has crossed a declared threshold, regardless of what is driving
it. `NvidiaGpuProvider.collect_readings`
(`src/aistack/providers/gpu/provider.py`) is the provider that reads this;
`aistack.runtime.gpu_anomaly.find_gpu_anomalies` is the correlation that
compares a reading against this register's declared thresholds;
`aistack.runtime.evaluate_gpu` is what cites `OPS-0004` against a
confirmed anomaly.

## Related Artifacts

- `OPS-0004` — Sustainability Qualifications, § *What each qualification
  means* (all four), § *Fifth reference case*
- `OPS-0005` — Storage Capacity Thresholds, the sibling register whose
  multi-kind threshold shape this one mirrors
- `OPS-0006` — Backup Freshness Thresholds, the sibling register whose
  "declared requirement, not incident" provenance this one mirrors
- `claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` — the health cockpit this
  register supports
