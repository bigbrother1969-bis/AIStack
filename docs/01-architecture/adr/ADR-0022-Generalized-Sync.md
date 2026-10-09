---
artifact:
  id: ADR-0022
  title: Generalized Sync
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Accepted
  owner: Architecture
  created: 2026-10-09
  updated: 2026-10-09

relations:
  references:
    - ADR-0003
    - ADR-0012
    - ADR-0016
    - ADR-0017
    - ADR-0019
---

# ADR-0022 — Generalized Sync

## Status

Accepted, 2026-10-09: the owner's answers of the same day decide § 1–5
and § 7; § 6 (a host executor) is the architecture that follows from
them, written here so it can be contested before the code exists.
`ADR-0016` § 3 allows acceptance the day of the proposal in the
development phase.

## Context

*Inventory of GIGABYTE, 2026-10-09.*

The *Selection* screen (`aistack.selection`, `/selection`, `ADR-0012`)
does one thing: the owner ticks directories of
`/media/TechData/Storage/Music`, and the tracks are hard-linked into
`/media/TechData/Storage/Music-Android`, the Syncthing folder
`music-android` shared with the phone (SM-A176B), within a declared
quota of 64 GB. Nothing is copied: a hard link costs no room.

The owner wants the same for every kind of content and four kinds of
destination. The contents sit on five disks of their own:

| Content | Directory | Disk |
|---|---|---|
| Books, BD, mangas | `/media/BD/Books`, `/media/BD/BD`, `/media/BD/Mangas` | `/media/BD` (1.8 TB) |
| Comics | `/media/Comics/Comics` | `/media/Comics` (916 GB) |
| Photos, images, videos, music | `/media/Multimedia/{Photos,Images,Videos,Music}` | `/media/Multimedia` (870 GB) |
| Documents | `/media/Documents/*` | `/media/Documents` (47 GB) |
| Films, series | `/media/Films/{Films,Series}` | `/media/Films` (1.8 TB) |
| Music (today's screen) | `/media/TechData/Storage/Music` | `/media/TechData` (1.8 TB) |

Syncthing runs in a container that sees the host's `/media` as `/data`;
it knows three devices: GIGABYTE itself, the phone, and the laptop
(`latitude`). No podcasts exist yet.

A hard link cannot cross a filesystem — and, inside a container, cannot
cross two bind mounts of the same filesystem either: the web container
sees `/media` read-only and only `Music-Android` read-write.

## Decision

Decided by the owner, 2026-10-09, except § 6.

### 1. Every content, by ticking directories

A content is a directory of GIGABYTE and the kinds of file it holds
(audio, images, video, books, comics, documents, or any file). The
screen is the one the music already has: the content's tree, a box per
directory, the room the selection takes against the destination's. A
content can exclude directories that must never be offered
(`/media/Documents/restricted`, the systems' own `lost+found` and
`System Volume Information`).

### 2. Four kinds of destination

- **A phone** and **any computer** (Mac, Windows, Linux): any device
  paired with GIGABYTE's Syncthing. One Syncthing folder per content
  and device.
- **The Kindle** (a recent model, which reads EPUB, the owner,
  2026-10-09): what is ticked is copied into its `documents` folder
  when it is plugged into GIGABYTE.
- **Any USB key or external disk** plugged into GIGABYTE: what is
  ticked for "USB" is copied into an `AIStack` folder on it.

### 3. One way only

GIGABYTE is the reference: a destination receives a selection, nothing
comes back. A file unticked is removed from the destination at the
next application — from the Syncthing folder (Syncthing then removes
it from the device), or from the `AIStack` / `documents` folder of a
removable medium; nothing else on the medium is ever touched.

### 4. No room spent on GIGABYTE

For a Syncthing destination, the folder lives on the same disk as its
content — `<disk>/.aistack-sync/<destination>/<content>` — so the
selection is hard-linked, never copied, as the music is today. Only a
removable medium receives copies. The music keeps its existing folder
(`Music-Android`, `music-android`): nothing is sent again.

### 5. AIStack creates the Syncthing folder, on the owner's click

A pair (content, device) with no Syncthing folder yet offers to create
it: AIStack adds the folder through Syncthing's REST API (path seen
from Syncthing's container, `/media` → `/data`) and shares it with the
device; the owner accepts the share on the device. Nothing is added to
Syncthing otherwise.

### 6. The screen records, a host executor applies

The web application records the selection (who ticked what, when) and
never writes into the content disks: an executor on the host,
`aistack-sync.timer`, every two minutes — the dock's pattern
(`ADR-0019`) — brings each destination to its recorded selection:
hard links for Syncthing folders, copies for a removable medium that is
plugged in. It needs no read-write mount in any container, and it sees
a USB key the moment the desktop mounts it. Each application is
recorded (files added, removed, bytes, duration); a removable medium
filled tells the vigil, which sends it to Gotify.

### 7. The room of a destination is declared

As today's 64 GB for the phone: a quota per destination, shared by all
its contents, checked before anything is applied; for a removable
medium, its free space, measured when it is plugged in.

## Implementation state

| Part | State |
|---|---|
| § 1, § 2 (Syncthing), § 4, § 5, § 7: declarations, the screen per content and destination, Syncthing folders | to do — tranche 4.1 |
| § 6 the host executor; § 2 (Kindle, USB) | to do — tranche 4.2 |

## Consequences

- The music screen becomes one pair among others; its folder, its
  selection and its quota are kept.
- AIStack writes to Syncthing's configuration for the first time — only
  on a click, only to add a folder and share it.
- Copies to a removable medium are the only place the sync spends room.

## Open Points

- Whether the web container's hard links into `Music-Android` ever
  worked since the Docker installation (2026-10-04): a link between two
  bind mounts fails with "Invalid cross-device link". § 6 removes the
  question; the test on GIGABYTE says whether today's screen was
  silently failing.
- Podcasts: declared when the directory exists.
