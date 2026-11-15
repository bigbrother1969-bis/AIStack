---
artifact:
  id: ADR-0026
  title: Arrivals
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Accepted
  owner: Architecture
  created: 2026-11-15
  updated: 2026-11-15

relations:
  references:
    - ADR-0009
    - ADR-0012
    - ADR-0020
    - ADR-0025
---

# ADR-0026 — Arrivals

## Status

Accepted, 2026-11-15, by the owner, the day of the proposal
(`ADR-0016` § 3). Decided with the owner the same day, while a writing service (KoboldCpp) was added to the
reference host and AIStack found it only as a Cockpit finding, to be
declared by editing a file: *"on fera aussi des ajustements dans AIStack
pour qu'il puisse identifier tout seul quand un nouvel hôte est mis en
ligne dans un container."*

## Context

*Measured on the reference host (MSI), 2026-11-15.*

AIStack already knows when a container runs that no service declares:
`aistack.runtime.inventory_gap` compares `service_categorization.yml` with
the containers found, locally and on the machines of the last network
discovery, and the Cockpit lists the gap (`OPS-0011`). Two things were
missing.

- **Nobody is told.** The gap is a finding like any other. The vigil
  (every 15 minutes) says a *silent host*, a failed restore test, a
  dock proposal; it does not say a new container. On the day `comfyui`
  and then `koboldcpp` were added, the owner learned of it by opening the
  Cockpit.
- **Nothing is proposed.** Closing the gap means finding the file,
  choosing the category, writing the entry by hand. The same goes for a
  machine: the network discovery lists what answers SSH and runs Docker,
  but only when the owner runs it, and nothing compares it with what is
  declared.

What a naive answer would get wrong, measured here:

- A container that lives a few minutes (a job, a build) is a gap for the
  length of its life. Said at the first sight, it would ring for nothing.
- The network discovery tries every declared SSH user name against every
  live host of the LAN. Its own code calls it *an action, not a passive
  read*: running it unattended changes what AIStack does to the network.
- The image holds no `nmap`, which the discovery runs first: inside the
  published image, the discovery returns no host at all.
- `hosts.yml` names the traced machines (`raspberry`, `gigabyte`) and the
  directory of their collector, not their address, so a machine found at
  `192.168.1.40` cannot be told to be `raspberry`.

## Decision

Decided by the owner, 2026-11-15: **detect and propose**, for containers
**and** machines.

### 1. Detect in the vigil, no new service

The vigil already passes every 15 minutes, renders the Cockpit and reads
its findings. `aistack.arrivals` reads the *undeclared* findings of the
inventory domain from that snapshot (local and remote containers alike)
and compares them with what it saw at the last pass
(`arrivals-state.json`). No Docker call of its own is needed to detect;
Docker is asked only for the image, ports and GPU request of a container
that is new.

### 2. Say it once, after two passes

A container is said to Gotify once, on the **second** pass in a row it is
seen (`confirm_passes`, 2). A container seen on one pass only is never
said, and is forgotten, so it is said again if it comes back. The line is
`Nouveau conteneur non déclaré : <name> — à déclarer dans « Nouveautés »`;
it is not urgent.

The first pass over a fresh state only **notes** what is there, as the
vigil's own first pass does: the containers undeclared on the day of the
installation are not news, they stay listed on the screen.

A message Gotify refuses is not noted: the same arrivals are tried at the
next pass.

### 3. Propose on a screen, write only on a click

The screen *Nouveautés* (LAN only, signed in, like the others) lists the
announced containers that no declaration covers and the owner did not set
aside, with what is known of each (where, image, ports, GPU) and a form
prefilled with a suggested name, the category to put it in (an existing
one, or a new one) and a description (the image and ports).

- **Declare** inserts the service into `service_categorization.yml`, as
  *text*: the file is the owner's, with comments and a layout of its own,
  so it is never re-dumped. The service goes after the last service of its
  category (or a category is added at the end); a dated copy
  (`…avant-arrivals-<date>`) is kept beside the file; the result is read
  back by the real loader, and replaces the original only if it loads and
  holds the container. A shape the editor does not know (a category with
  `services: []`) is refused with a message, never guessed.
  Administrators only (`ADMIN_ACTION`).
- **Ignore** puts the container in `arrivals-decisions.json`; **Restore**
  takes it out. The decisions are written only by the screen and the state
  only by the vigil: two files, so a click during a pass is never lost.
- The screen hides what a declaration now covers by reading the
  declaration itself, not the vigil's state: a container just declared
  disappears at once, not at the next pass.

### 4. Machines: propose the lines, never add

A machine that answers SSH and runs Docker, read from the last network
discovery (`network-docker-observation.json`), that no declaration names,
is proposed on the same screen with its address, the user that
authenticated, the number of containers, and the lines to add to
`hosts.yml` once the collector runs on it (`ADR-0020`).

Adding it is **not** a click: a host without a collector is a silent
host, a finding of its own. `hosts.yml` gains an optional `address:` so a
traced machine is recognized; `arrivals.yml` has `known_hosts:`; a click
on *Déjà connue* is a decision. The machines present in the **first
observation that holds any** are the baseline, not news; an observation
with no machine (a scan that failed) sets no baseline.

### 5. The scan is the owner's to switch on

The vigil runs the network discovery only when `arrivals.yml` says
`machine_scan_hours` (shipped: **0**, never). With a number (24, say) it
runs the discovery when that many hours have passed since the last one.
The owner can still run it by hand. The image now installs `nmap`; the key
named in `network_discovery.yml` must be readable inside the container.

### 6. Declared as the others are

`arrivals.yml` (shipped neutral: `confirm_passes: 2`,
`machine_scan_hours: 0`, `ignore: []`, `known_hosts: []`) sits in
`./config` like every declaration. The console gets a card.

## Consequences

- No new container, no new systemd unit: the vigil carries it.
- `declare` is the first code that **writes** `service_categorization.yml`
  (`aistack.architecture.yaml` says it is read-only and edited by hand;
  that sentence is amended). It writes one service, behind a click and a
  copy, and refuses what it does not understand.
- A container is said at the earliest at the second pass after it starts,
  15 to 30 minutes: slower than an event, by design.
- The owner's `./config/service_categorization.yml` is hand-edited and
  differs from the shipped one: the editor works on the file in
  `./config`, which is what the screens read (`aistack.config.configured`).
- Out of scope: stopping or removing a container, deciding a category for
  the owner, installing the collector on a machine, scanning the LAN
  without the owner's switch.

## Open points

- The suggested category is the first of the list; a suggestion from the
  image name (a GPU container beside the AI services) would help and is
  not made.
- The first scan with `machine_scan_hours` set will note every machine as
  known, including the ones the owner would have wanted proposed; they
  can be restored from *Écartés* only if they were set aside, not if they
  were baseline. Say it in the manual (done) or list the baseline on the
  screen, if it proves a nuisance.
- A container whose name changes at every recreation (a Compose project
  suffix) would be said at every recreation.
