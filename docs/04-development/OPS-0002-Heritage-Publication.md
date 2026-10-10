# OPS-0002 — Publication

*Version 2.0, 2026-10-10: condensed for 2.0.0-rc2. The full history of each
rule (version 1.19) is at the tag `archive/heritage-2.0.0-rc1`.*

How a change reaches the reference repository, then the mirrors, and how a
version and its image are published.

## Roles

| Role | What it is |
|---|---|
| **Workstation** | Where a patch is applied, checked and pushed to the SPOT. |
| **SPOT** | The Gitea repository, the one reference copy. |
| **Publisher** | A clone whose `origin` is the SPOT and which holds the mirror remotes. It checks what it pulls, then pushes to the mirrors. |
| **Mirrors** | GitHub and Codeberg. Never a reference, never an origin. |

One machine may hold several roles; which one holds which is the host's
business, not this document's. **The AI assistant holds none**: it works in a
throwaway clone and delivers every change as a patch, because pushing from a
clone of a mirror would make a mirror the origin of the code.

The repository is named **`AIStack`** everywhere (`pyproject.toml`,
`[project.urls]`). A URL is a route to it, not its identity: HTTPS, SSH on a
loopback or a local address reach the same SPOT, and none of them may change
the name.

## Applying a change

**1. On the workstation**, as one chain, so that any failure stops what
follows:

```bash
test -z "$(git status --porcelain)" \
  && test "$(git rev-parse --abbrev-ref HEAD)" = main \
  && source scripts/dev-env.sh \
  && git am --3way <patch>... \
  && ruff check src tests && mypy && pytest -q \
  && git push origin main
```

Patches are applied on the workstation only: applied on a second machine,
the same content becomes different commits, and that machine diverges at its
next pull.

**2. On the publisher**, the commit just pulled is checked again, then
published, still as one chain:

```bash
git pull --ff-only origin main \
  && source scripts/dev-env.sh \
  && ruff check src tests && mypy && pytest -q \
  && ./scripts/sync_mirrors.sh
```

A commit no machine has checked never reaches a mirror; the publisher's run
is also the one the image build relies on. The checks run once per pulled
commit: while `HEAD` stays the commit they passed on, the mirrors and the
image follow without running them again.

`sync_mirrors.sh` refuses any branch but `main` and a dirty tree, pulls the
SPOT before writing to any mirror, tries every mirror whatever the others
did, reports what each one received, and fails when any of them failed.

It also runs **unattended**, once a day on the publisher, its output going to
`logs/`. That run is a convenience: nothing depends on it, and the next
manual run publishes whatever a mirror missed.

## Publishing a version

**The release notes first.** Every version gets an entry in
`docs/03-handbook/RELEASE-NOTES.md`, in plain language, written before or with
the version bump in `pyproject.toml` — the only place the version is
declared; everything else reads it.

**The tag.** Only the `release(X.Y.Z)` commit is tagged `vX.Y.Z`, once it is
on the SPOT: never an earlier commit of the same series, never the later
commit that records the image digest. `sync_mirrors.sh` carries the tags to
the mirrors.

**A release candidate** (decided 2026-10-10, for 2.0.0): a version tried
outside the reference host first declares `X.Y.Z-rcN` (`X.Y.ZrcN` in the
installed metadata), is tagged `vX.Y.Z-rcN`, and its image is pushed under
that version only, never `latest`, which keeps naming the last release.
`install.sh` installs the version `pyproject.toml` declares, from that tag.

## Publishing the image

The image `bigbrother1969/aistack-core` is a build of one commit, and must be
traceable to it by someone holding only the image. It is built **after** the
commit is on the SPOT, on the publisher, once these hold:

```bash
test -z "$(git status --porcelain)" \
  && test "$(git rev-parse --abbrev-ref HEAD)" = main \
  && git fetch origin \
  && test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

— a clean tree, `main`, and a `HEAD` every recipient can fetch — plus the
checks of step 2 on that same commit, run again if `git fetch` brought a newer
one.

**The previous images first.** Every version `docker-compose.yml` lists as
current is pulled again and its digest compared with the one recorded there;
a mismatch is investigated before anything new is pushed.

Then:

```bash
VERSION="$(python3 -c 'import tomllib,pathlib; print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])')"

docker build -f Dockerfile \
  --label org.opencontainers.image.source="https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack" \
  --label org.opencontainers.image.revision="$(git rev-parse HEAD)" \
  --label org.opencontainers.image.version="$VERSION" \
  --label org.opencontainers.image.licenses="AGPL-3.0-or-later" \
  --label org.opencontainers.image.description="AIStack — Infrastructure Knowledge Platform" \
  -t "bigbrother1969/aistack-core:$VERSION" \
  -t "bigbrother1969/aistack-core:latest" .

docker push "bigbrother1969/aistack-core:$VERSION"
docker push "bigbrother1969/aistack-core:latest"
```

For a release candidate, leave out both `latest` lines. `latest` moves with
every release; a version tag never moves, and `docker-compose.yml` names a
version, never `latest`. The owner signs in to the registry himself; no
credential belongs here.

**Recorded** in `docker-compose.yml`, beside the services: the version, the
commit and the **digest** — a tag can be moved, a digest is the image. A
withdrawn or replaced entry is kept and explained, never deleted.

**Between two publications** the reference host runs `AISTACK_VERSION=dev`
in `.env`: code patches are deployed with
`docker compose build && docker compose up -d`, and a local build never
carries a published version's name. A published tag a build overwrote is
restored with `docker pull bigbrother1969/aistack-core:<version>`.

**How a recipient checks an image:**

```bash
docker inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' \
  bigbrother1969/aistack-core:<version>
git -C <clone> log -1 --format=%H <that revision>   # the commit exists, and is this one
```

That proves which commit the image claims, not that it holds that commit's
bytes: a label is metadata. What makes the label true is the procedure above.
`tests/unit/test_the_image_declares_what_it_ships.py` watches what once made
an image differ from its commit: bytecode left in the build context.

## Retiring a component

A component is retired when no host declares it any more — no unit, no
schedule, no container, no image — not when its code leaves the SPOT. The
order matters, because removing a container destroys the evidence of what
declared it:

1. **Inventory, while it still runs**: the compose file and project in the
   container's labels
   (`docker inspect <container> --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}'`),
   `systemctl list-unit-files`, the crontabs and `/etc/cron.d`.
2. **Stop and remove** the container, then the image.
3. **Remove every declaration** step 1 found, and only then record the
   retirement.

*2.0.0-rc2 is an instance: `sync_context_bundle.sh` was still run every six
hours by `/etc/cron.d/aistack-context-bundle` on the publisher, found by the
script's own tripwire before the script was removed.*

## Not here

Which machine holds which role and the addresses they use (the host's
configuration); the infrastructure that exposes the SPOT on the internet;
credentials of any kind.
