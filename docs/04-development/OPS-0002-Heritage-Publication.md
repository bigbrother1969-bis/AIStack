---
artifact:
  id: OPS-0002
  title: Heritage Publication
  type: Operations Procedure
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Operations
  created: 2026-08-27
  updated: 2026-08-27

relations:
  references:
    - FDN-0005
    - ENG-TEST-0002
    - GOV-0002
    - STD-0300
---

# OPS-0002 — Heritage Publication

## Purpose

This procedure states how a validated change reaches the Single Point Of
Truth, and how the SPOT reaches its mirrors.

Until 2026-08-27 it was stated nowhere. The README declared the *principle* —
the Gitea repository is the SPOT, GitHub and Codeberg are publication mirrors
and shall never be the origin of governed knowledge — and no artifact said
which role pushes where, in what order, or what must hold before each step.

That gap has a measured cost. On 2026-08-23 an agent read a `git remote -v`
listing and inferred a publication topology from it, confidently and wrongly,
because there was nothing to check the inference against. FDN-P-004 makes
knowledge the primary engineering asset; a procedure that lives only in the
owner's habits is not an asset, it is a dependency on one person being
available.

---

## Roles, not machines

This procedure names **roles**. Which machine holds which role is deployment
configuration and is deliberately not declared here — the same boundary the
owner drew on 2026-08-23 in GOV-0002/OS-015, where the expected state of a
deployment was ruled to be knowledge about a host rather than about the
product.

| Role | What it is |
|---|---|
| **Workstation** | Where a change is applied, verified and pushed to the SPOT. |
| **SPOT** | The Gitea repository. The single authoritative copy. |
| **Publisher** | A clone whose `origin` is the SPOT and which also holds the mirror remotes. It pulls from the SPOT and pushes to the mirrors. |
| **Mirror** | GitHub, Codeberg. Never authoritative, never an origin. |

One machine may hold several roles, and the workstation and the publisher may
be the same. What matters is that the *order* below holds, not how many
machines it runs on.

### The agent holds no role

An AI assistant working on this heritage does not publish. It works in a
throwaway clone, and delivers every change as a patch the owner applies on
the workstation.

The reason is structural rather than cautionary: in such a clone `origin` is
whatever the agent cloned from, which is typically a mirror. Pushing from it
would make a mirror the origin of governed knowledge, which is the one thing
the README forbids by name. GOV-P-001 says the same at the level of
authority — the AI never creates authoritative knowledge.

---

## The canonical name

The repository is **`AIStack`**. That spelling is declared in
`pyproject.toml` under `[project.urls] Repository`, which is a project fact,
identical on every machine.

**A URL is a route, not an identity.** The same SPOT is legitimately reached
over HTTPS through a public name, over SSH on a loopback from a co-located
clone, or over a local network address. None of those is more canonical than
another, and a clone whose remote is a tunnel or a loopback is not a lesser
clone — which is why the Context Bundle publishes `repository_url` from the
declared project fact and not from any clone's remote.

What a route may not do is change the name. Read off the publication output
of 2026-08-23, and still true as of 2026-08-27: the repository is addressed
as `AISTack` on Codeberg and in the publisher's `origin`, and as `AIStack` on
GitHub and in `pyproject.toml`. Gitea tolerates case in repository names, so
nothing ever failed and nobody saw it for weeks.

---

## The order

```text
Workstation                SPOT                 Publisher            Mirrors
     │                       │                      │                   │
  apply                      │                      │                   │
     │                       │                      │                   │
  verify                     │                      │                   │
     │                       │                      │                   │
  push ────────────────────► │                      │                   │
                             │ ◄──────── pull ───── │                   │
                             │                      │                   │
                             │                      │ ──── publish ───► │
```

### 1. Apply and verify, on the workstation

```bash
git status --porcelain          # must be empty
git rev-parse --abbrev-ref HEAD # must be main

git am --3way <patch>...        # in the order they were produced

source scripts/dev-env.sh
pytest -q
python3 -m aistack.cli.knowledge_integrity
```

The environment command is the one ENG-TEST-0002 names, and the reason it
names that one is recorded there: it is the file that *provides* the
environment, not merely the one that declares it.

A change is not publishable until the suite passes and the integrity report
reads `clean: True`. STD-0300 governs what that report must contain.

**Patches apply on the workstation only.** Applying the same patches on a
second machine produces different commits for the same content, and the
second machine then diverges from the SPOT at its next pull.

### 2. Push to the SPOT

```bash
git push origin main
```

### 3. Publish the mirrors, on the publisher

```bash
./scripts/sync_mirrors.sh
```

The script performs the whole of step 3, and its guarantees are part of this
procedure rather than incidental to it:

- **it refuses any branch but `main`**, because publishing a working branch
  would merge it into the SPOT;
- **it refuses a dirty tree**;
- **it pulls the SPOT before writing to any mirror.** That pull is the only
  step that still stops the run. Publishing to a mirror without having
  reached the SPOT would make the mirror the source of a state the SPOT never
  had;
- **it attempts every mirror whatever the others did**, and names each
  failure at the end. One mirror is not a dependency of another
  (GOV-0002/OS-009);
- **it fails when any mirror failed**, so a partial synchronization is not
  indistinguishable from a complete one to whatever reads the exit code;
- **it reports what each mirror received**, by commit, rather than reporting
  that the script ran.

---

## What can fail, and what it does not affect

Recorded from occurrences rather than imagined.

**The workstation's route to the SPOT can be down while the SPOT is
healthy.** On 2026-08-23 a push failed with HTTP 530 — a Cloudflare code
wrapping an origin failure, not a Git or authentication error, which would
have been 401 or 403. The public route depends on infrastructure outside this
project. The SPOT itself was serving throughout.

**That failure does not reach the chain SPOT → mirrors.** The publisher's
`origin` is co-located with the SPOT, so it publishes whatever the SPOT holds
regardless of the public route. Only the workstation's leg was blocked, and
the correct response is to restore the route or use another one — not to
publish from elsewhere.

**A mirror can fail while the others are reachable.** On 2026-08-21 GitHub
rate-limited the host and the run ended there, leaving Codeberg — reachable
throughout — unpublished. That is why the script attempts each independently
(GOV-0002/OS-009).

**The script can be replaced by the pull it performs**, since the SPOT holds
the script. Everything it does now lives inside a function invoked on the
last line, so the whole file is parsed before any of it runs
(GOV-0002/OS-010). Observed on 2026-08-23: the run that delivered that very
fix executed the old file to completion, printing the old messages.

---

## What is deliberately not here

- **Which machine holds which role**, and the addresses they use. Deployment
  configuration (GOV-0002/OS-015).
- **The infrastructure that publishes the SPOT to the public internet.** It
  serves the owner's wider environment and is not part of AIStack.
- **Credentials.** No token, password or key belongs in this heritage, and
  the owner authenticates every step personally.
