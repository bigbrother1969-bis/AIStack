---
artifact:
  id: RELEASE-NOTES
  title: Release Notes
  type: Release Notes
  semantic_type: Knowledge Artifact
  domain: Foundation
  criticality: C2
  confidence: Declared
  version: 1.4
  status: Draft
  owner: Foundation
  created: 2026-09-04
  updated: 2026-09-12

relations:
  references:
    - OPS-0002
    - GOV-0002
    - STD-0100
---

# Release Notes

## Purpose

What changed for someone using AIStack, one published version at a time —
in plain language, not in the governance vocabulary the rest of this
heritage uses to talk to itself.

## Scope

One entry per version `pyproject.toml` has ever declared and
`bigbrother1969/aistack-core` has published to Docker Hub, oldest at the
bottom. An entry is written when the version is bumped, per `OPS-0002` §
*Recording what's new* — `GOV-0002/OS-055`. This document does not replace
`docker-compose.yml`, which is where the digest that proves a build lives;
it says what the build was *for*.

---

## 0.7.0 — 2026-09-12

**Everything below is what `PLAN-J11-CONSOLE-2026-09-11.md` §10 and §11
added on top of `0.6.0`, the same day: `architecture.html` grows three new
sections, and AIStack can now see Docker containers on machines other than
the one it runs on.**

- **Docker dependency graph.** `architecture.html` gained a new view: the
  real `depends_on:` relationships between containers, read straight from
  each Compose project's own `docker-compose.yml` files — a project's
  containers shown as a connected graph, not a flat list, an arrow drawn
  only where a real dependency was actually read, never guessed.
- **External network topology and hardware inventory.** A new section
  names what sits outside the Docker layer entirely: the external services
  the homelab depends on (registrar, DNS/CDN, router, mail) and the two
  physical machines that run everything — model, CPU, RAM, disks, GPU —
  as a declared fact sheet instead of something to remember.
- **Live health metrics from Beszel.** Another new section reads real-time
  status, CPU, memory, disk, temperature, load and uptime for every system
  Beszel already monitors, shown alongside the rest of the architecture
  page instead of in a separate tool.
- **Network-wide Docker discovery.** A new, explicitly-triggered command
  (`aistack.cli.network_docker_discover`) scans the declared LAN, tries
  each declared SSH username against every host it finds alive, and
  reports back every Docker container running anywhere on the network —
  not only on the one machine AIStack itself runs on. Its first real run
  found containers on two machines this project had never observed
  before.
- **A LAN-only screen to manage that scan's candidate SSH usernames**, a
  new fifth card on the console, so adding a machine to the scan no longer
  means hand-editing a YAML file over SSH.

Before this build, `0.6.0` was re-verified against its recorded digest
(`GOV-0002/OS-047`) — pull matched.

`bigbrother1969/aistack-core:0.7.0`, built from `0f511b6`, digest
`sha256:61a18a664a2e41d22c2e682b1cc0d1e0d09e57806c2b92f3cde44f091013c5ba`.
1751 tests, 73 knowledge artifacts, `clean: True`.

## 0.6.0 — 2026-09-12

**Everything below shipped in the eight days since 0.5.0 — the version number
just never moved while it did. This entry catches it up in one go, and also
carries `evaluate` (below), which had briefly used this same number and lost
it to an undocumented revert — explained where that entry now stands,
retracted.**

- **`architecture.html`, rendered for real.** AIStack's own topology graph —
  built from the same Docker infrastructure discovery `0.5.0` already had —
  is now a self-contained page instead of only raw catalog JSON.
- **Health Cockpit.** One scored dashboard across four domains: Storage,
  Services, Backup/DR, and GPU. Each domain is instrumented against a real
  incident or a real declared threshold on the reference host, not a
  generic rule guessed in the abstract.
- **Console — one entry point for everything above.** A single page linking
  Selection UI, Priority CPU, Architecture, and Health Cockpit. All four are
  now reachable over HTTPS from outside the LAN, not just on the local
  network.
- **Quiet foundation work, no visible capability yet:** a shared event/
  version/provenance model that the project's four separate history
  mechanisms now all speak, and governed contracts for evidence,
  observation, collection and correlation. This is what the next phase (a
  full historical "time machine" — replaying what the system knew at any
  past moment) is built on, not a feature in itself yet.
- `ruff` and `mypy` adopted project-wide, gated in the same publishing
  chain as everything else.

`bigbrother1969/aistack-core:0.6.0`, built from `4d68ffc`, digest
`sha256:28a3e4e621d83c563725e08fd6e774158f2752b0d4e3a2008f60c1496a986a47`.
1549 tests, 73 knowledge artifacts, `clean: True`.

## 0.6.0 — 2026-09-11, retracted 2026-09-12

**The finding described below is not retracted — it ships in `0.6.0` above,
same as everything since `0.5.0`. What's retracted is only this entry's
claim to the tag: `pyproject.toml` reverted to `0.5.0` the same day this
entry was built (one unlabeled commit, folding in the Storage domain
alongside the version line, with no doc update to match), so by the time
the entry above needed a number, `0.6.0` was free again rather than taken.
Kept here rather than erased — the same reasoning `1.0.0`, right below,
already gives for the same kind of correction. The image itself is
preserved, retagged `bigbrother1969/aistack-core:0.6.0-retracted` now that
the live `0.6.0` tag points elsewhere.**

**The first qualified finding, derived end to end: two separately-collected
pieces of evidence correlated into one governed conclusion for the first
time. VS-4 closes three more criteria (4.2, 4.4, 4.5).**

- **New: `evaluate`.** Unexplained CPU consumption — a container using
  resources nobody declared an expectation for — is now correlated against
  the host's own temperature, at or above each sensor's own declared
  threshold, into one `RuntimeFinding`: `energy inefficiency` alone, or
  `energy inefficiency` and `sustainability anomaly` together when the host
  also reads hot. Wired end to end into `runtime_diagnose`: a live sweep of
  the reference deployment reports these the same way it already reports a
  log-signature finding.
- **New: a finding can cite a reading, not only a log line.** A
  `CitedReading` attaches the raw CPU or temperature reading a provider
  collected to a finding, named by the provider that collected it (`docker
  stats`, `sensors`) — alongside the existing log-line evidence, unchanged.
- Host temperature is read in a live sweep for the first time —
  `HostProvider.collect_temperatures` existed since `0.5.0` but nothing
  called it.

`bigbrother1969/aistack-core:0.6.0-retracted` (built as `:0.6.0`), built
from `a823190`, digest
`sha256:203bec639e4bae1240bc1d19bd9485e7eb2c24f185565aa23f7f2925c07e3109`.
1191 tests, 69 knowledge artifacts, `clean: True`.

## 1.0.0 — declared 2026-09-11, retracted 2026-09-11

Declared prematurely, on the mistaken assumption that the first qualified
finding (`evaluate`, below) was the 1.0 boundary. It is not: the same day
this version was declared, a separate, richer predecessor project was
recovered — a homelab health dashboard, a technical-debt score, and an
interactive architecture cartography, none of it living in AIStack yet —
and the project's own trajectory reserves 1.0 for the point where that
integration is complete
(`claude/PLAN-J6-HOMELAB-DASHBOARD-INTEGRATION-2026-09-11.md`), not for
`evaluate` alone. Corrected to **0.6.0**, below — same work, same day.
Kept here rather than erased, so the record shows what was renumbered and
why — the same reasoning `0.1.0`'s entry gives for the same kind of
correction.

`bigbrother1969/aistack-core:1.0.0`'s digest was pulled and re-verified
against its record before the corrected build (`GOV-0002/OS-047`) — it
matched: `sha256:efcb70b1a3be5d71f444d91a0483b5a632def704815079e80f1434976d5823c3`.
No divergence; the tag simply named the wrong version.

## 0.6.0 — 2026-09-11

**The first qualified finding, derived end to end: two separately-collected
pieces of evidence correlated into one governed conclusion for the first
time. VS-4 closes three more criteria (4.2, 4.4, 4.5).**

- **New: `evaluate`.** Unexplained CPU consumption — a container using
  resources nobody declared an expectation for — is now correlated against
  the host's own temperature, at or above each sensor's own declared
  threshold, into one `RuntimeFinding`: `energy inefficiency` alone, or
  `energy inefficiency` and `sustainability anomaly` together when the host
  also reads hot. Wired end to end into `runtime_diagnose`: a live sweep of
  the reference deployment reports these the same way it already reports a
  log-signature finding.
- **New: a finding can cite a reading, not only a log line.** A
  `CitedReading` attaches the raw CPU or temperature reading a provider
  collected to a finding, named by the provider that collected it (`docker
  stats`, `sensors`) — alongside the existing log-line evidence, unchanged.
- Host temperature is read in a live sweep for the first time —
  `HostProvider.collect_temperatures` existed since `0.5.0` but nothing
  called it.

`bigbrother1969/aistack-core:0.6.0`, built from `a823190`, digest
`sha256:203bec639e4bae1240bc1d19bd9485e7eb2c24f185565aa23f7f2925c07e3109`.
1191 tests, 69 knowledge artifacts, `clean: True`.

## 0.5.0 — 2026-09-04

**A stabilization release: no new capability, eight pieces of tracked debt
closed, two real defects fixed.**

- The open-item register (`GOV-0002`) went from eight open entries to
  zero. Among them: three foundational documents (the principles
  registry and the two testing-environment standards) moved from `Draft`
  to `Published`; the deployment host now has a named, verified way to
  run AIStack without hand-setting `PYTHONPATH` on every command
  (`ADR-0001` § *Deployment host*).
- **Fixed:** the Context Bundle always reported its own repository
  location as `"unknown"`, even when the information was sitting right
  there in the bundle's own manifest. It now reads it.
- **Fixed:** files moved to the archive folder (`docs/99-archive`) were
  still being treated as part of the governed knowledge base instead of
  being set aside — the exclusion existed for `docs/99-meta`, one
  directory over, and missed this one by a name.
- **First real exercise of the "an image stays verified" rule**
  (`GOV-0002/OS-047`): before this version was built, `0.4.0` was pulled
  back from Docker Hub and its digest checked against the one on record —
  it matched.

`bigbrother1969/aistack-core:0.5.0`, built from `57290fa`, digest
`sha256:3def537335f5f9f36d2824f2c6d56e0c4f5c7232017be36b93bf78a307816896`.
940 tests, 66 knowledge artifacts, `clean: True`.

## 0.4.0 — 2026-09-03

**The CPU priority feature generalizes from one hardcoded app to any
number of declared ones.**

- What used to be "watch Jellyfin, throttle these fourteen named
  containers" became a declared list: any container can be named a
  priority app, each with its own CPU ceilings and its own way of
  detecting activity — asking an app's own API (as Jellyfin already did)
  or reading its live CPU usage for a container with no API of its own.
- A container Docker reports that nobody has classified is now left
  alone entirely, rather than assumed to belong to the fourteen-name
  list.
- New screen: `priority_ui`, to add, edit or remove a priority app or a
  background container without hand-editing YAML.
- CPU boost/throttle decisions are now written to a queryable history —
  when a container was boosted, why, and for how long.

`bigbrother1969/aistack-core:0.4.0`, built from `8757605`, digest
`sha256:daf46c76b309e047c8801a25857b1328c01fc69c84c25d1ac333e05c8bb2f9fb`.
853 tests, 66 knowledge artifacts, `clean: True`.

## 0.3.0 — 2026-09-03

**Two new capabilities, running live on the reference host.**

- **Resource priority monitor**: while Jellyfin is playing something,
  AIStack gives it more CPU and turns the rest of the background
  containers (the `*arr` stack, torrent client, etc.) down — then puts
  everything back once playback stops. Runs as its own service on the
  host.
- **Selection UI redeployed as a systemd service**, off the ad hoc
  terminal session it used to need.

`bigbrother1969/aistack-core:0.3.0`, built from `7fab030`, digest
`sha256:55f9cd02711462306eb434a6c4184936b7a7fa1a28ddc7f374bea2248fde0376`.
823 tests, 66 knowledge artifacts, `clean: True`.

## 0.2.0 — 2026-08-29

**The first image published under a governed procedure.**

`0.1.0` (below) had shown what publishing without one costs. `OPS-0002` §
*Publishing an image* exists because of that, and this is the first build
to go through it: a clean tree, `main`, `HEAD` equal to the published
commit, and a passing suite, checked in that order before the image is
built at all.

`bigbrother1969/aistack-core:0.2.0`, built from `0a7ec1a`, digest
`sha256:3ee7cf1fae80cce7c84f404f5354f5edeeeddbf950e299c4a2a8dcb1f4aa194f`.
668 tests, 66 knowledge artifacts, `clean: True`.

## 0.1.0 — 2026-08-19, deleted 2026-08-23

The first published image, built without the procedure `0.2.0` introduced.
It carried compiled bytecode the project's own knowledge base had no
record of. Rather than rebuild it retroactively, the owner deleted it —
`GOV-0002/OS-011` records the reasoning: *"a rebuilt image would have to be
verified before publication and then stay verified; an image nobody pulls
cannot diverge from the heritage that describes it."* Kept here rather than
erased, so the record shows what was unpublished and why, not just what
survived.

---

## Everything AIStack does, as of this release

Not what changed — what runs, as of 0.7.0 (2026-09-12), taken together.

- **Docker infrastructure discovery.** Point AIStack at a Docker host and
  it produces a governed catalog of what is running: identity, image,
  state, published ports, mounts, and — as of 0.7.0 — the real
  `depends_on:` relationships between containers, read from each Compose
  project's own files — regenerated the same way every time, from the
  host, not from what someone remembers about it.
- **Architecture, visualized.** `architecture.html` renders that same
  discovery as a self-contained topology graph, plus — as of 0.7.0 — a
  Docker dependency view, a section naming the external network topology
  and the hardware each machine runs, and a live Beszel health-metrics
  section — a real page, not raw catalog JSON, kept current every time
  it's regenerated.
- **Network-wide Docker discovery.** A separately-triggered scan of the
  declared LAN, over SSH, reports Docker containers running on machines
  other than the one AIStack itself runs on — new as of 0.7.0.
- **Health Cockpit.** One scored dashboard across four domains — Storage,
  Services, Backup/DR, GPU — each instrumented against a real incident or
  a real declared threshold on the reference host.
- **Console.** One entry point linking Selection UI, Priority CPU,
  Architecture, Health Cockpit and — as of 0.7.0 — the LAN-only network
  discovery screen, all reachable from the same page.
- **Context Bundle — self-onboarding for an AI assistant.** A single
  portable archive carries the project's whole governed knowledge base,
  with a manifest that proves what commit it was taken from and lets a
  recipient verify two bundles carry the same content without trusting
  whoever sent it. This is how a new AI session, or a new contributor,
  gets up to speed without reading the repository's entire history.
- **Knowledge integrity validation.** Sixteen checks run against the
  governed documentation on every test suite and before every
  publication — missing metadata, broken cross-references, undated
  claims about a moving system, decisions nobody recorded as implemented
  or abandoned, and more. `clean: True` is what gates a release.
- **Runtime diagnosis.** A sweep of the Docker host, no container named,
  qualifies log lines against declared signatures, flags CPU consumption
  and development options (like `--reload`, the bug that started this
  capability) left enabled in a permanent service — and, as of 0.6.0,
  correlates unexplained consumption against the host's own temperature
  into one finding citing `OPS-0004`'s vocabulary: energy inefficiency
  alone, or energy inefficiency and sustainability anomaly together when
  the host also reads hot. Every finding grounds against known service
  context (`OPS-0003`) and cites the evidence it was built from — a log
  line, or now a raw reading.
- **CPU resource priority scheduling.** Declared priority applications
  (Jellyfin, as of 0.5.0) get more CPU while active and give it back once idle;
  everything else is throttled down for the duration. Detection is
  pluggable — an app's own API, or its live CPU usage — and every
  boost/restore decision is recorded, queryable later.
- **Music sync selection.** Choose, under a real capacity limit, what
  part of a media library syncs to a device — a checkbox screen backed by
  a tested selection engine, materializing the result by hard link rather
  than by copy, and telling the truth about what's selected, what's
  built, and what's actually landed on the device.
- **A governed documentation heritage, self-applied.** Every architectural
  decision, standard, and open question this project has is itself a
  checked, cross-referenced, versioned knowledge artifact — including the
  register that tracks what is still open (`GOV-0002`) and the procedure
  that governs how a change reaches the world (`OPS-0002`). AIStack's
  claim that infrastructure knowledge can be governed is tested against
  itself first.

---

## Related Artifacts

- `OPS-0002` — Heritage Publication, § *Publishing an image*, § *Recording
  what's new*
- `GOV-0002` — Open State Register
- `docker-compose.yml` — the digest that proves each build, alongside the
  summary this document gives it
