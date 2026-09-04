---
artifact:
  id: OPS-0002
  title: Heritage Publication
  type: Operations Procedure
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.12
  status: Draft
  owner: Operations
  created: 2026-08-27
  updated: 2026-09-04

relations:
  references:
    - FDN-0005
    - ENG-TEST-0002
    - GOV-0002
    - STD-0300
    - RELEASE-NOTES
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

What a route may not do is change the name, and for weeks the routes did not
agree. Read off the publication output of 2026-08-23, the repository was
addressed as `AISTack` on Codeberg and in the publisher's `origin`, and as
`AIStack` on GitHub and in `pyproject.toml`. Gitea tolerates case in
repository names, so nothing ever failed and nobody saw it. Codeberg does not
tolerate it, and the two mirrors of one SPOT carried two names.

Corrected on 2026-08-27 by GOV-0002/OS-028, and read off the publication
output of the same day at 15:02 — which is where a remote name can be
observed rather than asserted:

```text
workstation → https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack.git
publisher   → ssh://127.0.0.1:2222/fabrice.persiaut/AIStack
github      → github.com:bigbrother1969-bis/AIStack.git
codeberg    → codeberg.org:bigbrother1969/AIStack.git
```

**This paragraph went on describing the divergence as current for the rest of
that day**, hours after OS-028 closed it, on three forges. It read *still true
as of 2026-08-27*, and the date was right.

`undated-assertions` cannot see a sentence like that: it is dated, and **a
date is not a measurement.** The file was revised three times the same
afternoon — v1.3, v1.4, v1.5 — and this section was re-read on none of them.
The same disease is the subject of GOV-0002/OS-036, in a register entry rather
than in a procedure.

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

Run this from the workstation's clone, as one sequence:

```bash
test -z "$(git status --porcelain)" \
  && test "$(git rev-parse --abbrev-ref HEAD)" = main \
  && git am --3way <patch>... \
  && source scripts/dev-env.sh \
  && pytest -q \
  && python3 -m aistack.cli.knowledge_integrity
```

**The chaining is the procedure, not a shell habit.** Until version 1.5 the
same six commands were shown as six lines, the first two carrying `# must be
empty` and `# must be main` as comments. A precondition written in a comment
is checked by whoever reads it, which is to say on the days they are looking.
`test` fails, and a failure stops what follows.

It makes the last line a gate rather than a report:
`aistack.cli.knowledge_integrity` exits non-zero on a blocking finding, and
nothing chained after it runs. In six separate lines that exit code is printed
and discarded.

**The block names no path**, and that is the same decision as *Roles, not
machines*. It was written otherwise on 2026-08-27 — a session prefixed this
sequence with a `cd` to the publisher's path while instructing the
workstation. The `cd` failed, the lines after it ran anyway, and the patches
were applied wherever the shell happened to be. It was the right repository by
coincidence.

The environment command is the one ENG-TEST-0002 names, and the reason it
names that one is recorded there: it is the file that *provides* the
environment, not merely the one that declares it.

A change is not publishable until the suite passes and the integrity report
reads `clean: True`. STD-0300 governs what that report must contain.

**One exception, and it is narrow: a `WARNING` an open register entry names.**
A blocking finding never — those stop the chain by exit code, and nothing here
weakens that.

The exception exists because without it **a rule can block its own repair.**
Raising a check's severity states that the heritage is non-conformant; if that
same state forbids publishing, the commits that bring the heritage into
conformance cannot reach the SPOT. The rule would hold the fix hostage to
itself. Decided 2026-08-27 by the owner, while sequencing exactly that case in
GOV-0002/OS-038.

**What the entry buys is that the warning is explained.** A report carrying a
warning nobody can account for teaches its readers to scroll past warnings,
which costs more than the warning was worth. The register entry names the
condition, carries the work, and dates it.

*Measured while writing this: `aistack.cli.knowledge_integrity` exits non-zero
on a **blocking** finding only, so a warning has always published in practice —
the chain never stopped for one. This paragraph does not loosen a gate; it
states what the gate is, and adds a condition a reader can audit where there
was an absolute rule the mechanism did not enforce.*

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

## Publication also runs unattended

The three steps above describe a person publishing. **They are not the only
way this heritage is published**, and until 2026-08-27 no artifact said so.

Two schedules exist on the publisher, both discovered by accident while
renaming a directory:

| Cadence | What runs | Where its output goes |
|---|---|---|
| every 6 hours | `scripts/maintenance/sync_context_bundle.sh` — regenerates the projection | a log file under `logs/` |
| daily | `scripts/sync_mirrors.sh` — publishes the mirrors | a log file under `logs/` |

An unattended run is the same run. It refuses a working branch and a dirty
tree, it reaches the SPOT before writing to any mirror, and since 2026-08-23
it exits non-zero when a mirror failed.

**A schedule is a convenience. The governed run is the manual one**, decided
by the owner on 2026-08-27. Both schedules redirect their output into a file,
so a failure that would be unmissable in a terminal is a line nobody opens —
and that is accepted rather than overlooked. Nothing depends on a nightly
publication having happened: the next manual run pulls the SPOT first and
publishes whatever the mirrors are missing, which is what the step-3
guarantees above are for.

What that costs is a delay, bounded by the next person who publishes. What it
buys is that no one has to read a machine. The alternative — a mailbox, or a
verdict written where the next session looks — was weighed and declined; it
would add a thing to watch in order to protect a thing nothing depends on.

That reading is written here because the opposite reading is the intuitive
one, and because GOV-0002/OS-009 established that a run must report what it
did. It must. What is decided here is who has to be listening.

**The six-hourly regeneration is not a convenience in the same way**, and it
does not get the same answer. Until 2026-08-27 it invoked `python3` directly,
so the projection it produced four times a day was generated by whichever
interpreter the host distribution installs. ENG-TEST-0002 is C3 and asks for
reproducibility across environments; GOV-0002/OS-019 measured what that axis
costs — the same contract inventory gave 20 orphans on one interpreter and 22
on another, at the same commit.

It now sources `scripts/dev-env.sh` and **refuses to run** when the declared
interpreter is not the one it gets. A projection is a published artifact; a
delayed one is a nuisance and a doubtful one is a lie. The refusal goes to
standard error, which cron mails, rather than to the log file the paragraph
above accepts nobody reads.

---

## Retiring a component

Publishing is how something enters the world from this heritage. Retiring is
how it leaves, and **it is not finished when the code is removed from the
SPOT.**

A component is retired when nothing on any host still declares it: no service
unit, no schedule, no container, no image, no path referenced by any of them.
Until then the repository has removed a component and the world has not.

### The order, and why it is an order

**1. Inventory what declares it, while it still runs.**

```bash
docker inspect <container> \
  --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}'
docker inspect <container> \
  --format '{{index .Config.Labels "com.docker.compose.project"}}'

systemctl list-unit-files | grep <name>
crontab -l | grep <name>
```

A running container carries the absolute path of the file that declared it,
written into its own labels by Compose. **That evidence is stored in the
container and is destroyed by the removal it is needed for.**

**2. Stop and remove** — container, then image.

**3. Remove every declaration found in step 1**, and only then record the
retirement.

### When step 1 was skipped

It is recoverable, and it is not equivalent. What is left is a search:

```bash
docker compose ls --all
grep -rln "<name>" /srv ~ --include="*.yml" --include="*.yaml"
```

A search proves what it walked. The label proved what declared the component.
The difference is not academic: a declaration under a path nobody thought to
search reads exactly like no declaration at all.

### The rule was written from three instances

- `aistack-backend` was decided for retirement on 2026-08-23 (GOV-0002/OS-012)
  because it answers an unauthenticated API holding a writable Docker socket.
  The decision was taken; the component ran for four more days.
- `aistack-funnel-inbox.service` was found on 2026-08-27 enabled on the
  publisher, with a restart counter at 30 103, for a component whose committed
  half had been removed on 2026-08-23 and whose entry point had never been
  committed at all (GOV-0002/OS-032). It had never once started.
- `aistack-backend` again, on 2026-08-27: the container and the image were
  removed before anything asked what declared them, so the Compose label went
  with the container. The recovery search named exactly one file — the
  ancestor's `docker-compose.yml`, which FDN-0005 declares an archive — and by
  then the retirement had been recorded as complete. GOV-0002/OS-036.

Neither of the first two was noticed by anything; the second had been failing
every five seconds since 2026-07-31.

**The third is what turned an obligation into an order.** Version 1.3 of this
section, written the same morning, stated that a retirement has a second half.
It did not state that the first half destroys the evidence for the second, and
the run that followed it three hours later removed a container without reading
its labels.

**This is a procedure and not a check, and that is deliberate.** GOV-0002/OS-015
settled that this repository describes a product rather than a host, and the
heritage does not read service units or crontabs. What it can do is state that
a removal has a second half, so that whoever performs the first knows the work
is not done — and so that the register entry closing a retirement says both
halves happened.

The boundary is narrow on purpose. This does not make the expected state of a
host governed knowledge; it makes the *consequence of a removal* part of the
removal. A host may run whatever it likes. What it may not do is go on running
something this heritage has decided to stop shipping, without anyone knowing.

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

## The Context Bundle, and handing one over

**A Context Bundle is regenerated whenever the governed documentary heritage
changes.** Decided 2026-08-28 by the owner. This is not an added constraint: it
states what step 1 already does, so the property becomes opposable instead of
depending on the order in which someone typed two commands.

`pytest` regenerates the projection, at the `HEAD` the workstation is standing
on. In the sequence above that `HEAD` is the commit just applied, so the bundle
declares the commit it projects.

**Two different things keep that true, and neither covers the other.**
`test_the_projection_declares_the_commit_it_projects` refuses a projection that
names no commit — the export falls back to `unknown` whenever git cannot answer,
silently. What it cannot see is an uncommitted change under `docs/`: it reads
`git rev-parse HEAD` and so does the export, so the content can be ahead of the
commit the bundle declares and the comparison still holds. **That half is this
procedure's job**: step 1 refuses to start on a dirty tree, which is why
`test -z "$(git status --porcelain)"` is the first term of its chain and not a
convenience.

*Both statements were measured by mutation on 2026-08-28, in that order: the
test was written believing it refused a premature regeneration, and it does
not.*

**The bundle is not in the repository.** `context/bundles/` is in `.gitignore`:
a projection is a generated artifact, disposable, and rebuilt from the SPOT at
will. Two consequences that a reader should not have to derive:

- **there is no bundle to keep up to date** — there is a command that produces
  a current one, and it is the one step 1 runs;
- **freshness is not an age.** A bundle is current when the governed documents
  it projects are the SPOT's, whatever its date. `content_hash` in
  `manifest.json` decides it in one comparison, for anyone holding the
  repository.

### A moved `HEAD` is not by itself a stale bundle

**Two statements of this rule sat side by side and did not say the same thing**,
which was found on 2026-08-29 by running the published image on a host one
commit behind and reading what it validated:

| | What makes a bundle stale |
|---|---|
| this section | a **governed artifact** changed |
| `test_the_projection_declares_the_commit_it_projects` | **`HEAD` moved**, for any reason |

They are both right about their own subject and neither is the whole rule. **The
procedure protects content; the test protects traceability.** A commit that
touches no governed artifact — `f6a9580`, which changed only `docker-compose.yml`
— leaves an existing bundle exact in content while its `source_commit` becomes an
ancestor of the SPOT's `HEAD`.

**So the rule, stated once and completely.** A bundle is stale when either holds:

- **a governed artifact changed** since the commit it declares. The bundle then
  describes a heritage that no longer exists, and regenerating is the only
  answer;
- **it declares no commit, or one the SPOT does not carry.** Then nobody can
  check it at all, whatever its content — which is what the guard test refuses
  and why it compares against `HEAD` rather than against a content hash.

**A `source_commit` that is merely an ancestor of `HEAD` is neither.** It is a
bundle that can still be checked and whose content may be exact, and a recipient
holding the repository settles it in one command:

```bash
git diff --name-only <source_commit>..main -- docs README.md \
  | grep -E '\.md$' \
  | grep -v '^docs/99-meta/'
```

Empty output means the governed heritage did not change and **the bundle is
current despite naming an older commit**. The paths are not a convention: they
are `INCLUDED_PATHS` and `EXCLUDED_PATHS` in
`src/aistack/context_bundle/eligibility/rules.py`, which is the allow list that
decides what a projection carries.

*Written 2026-08-29 on the owner's decision, after the ambiguity was measured
rather than argued. **Neither statement was wrong and nothing had to be
repaired** — what was missing was the sentence relating them, which is the same
shape W-13 and W-15 had on 2026-08-28 and the third time this week that two true
statements of one rule turned out never to have been introduced to each other.*

### Handing a bundle to someone

A bundle that leaves this machine is one produced by step 1, and it carries what
a recipient needs to check it without trusting the sender:

| What the recipient reads | In | What it settles |
|---|---|---|
| `source_commit` | `manifest.json` | which commit the projection claims |
| `content_hash`, `hash_algorithm` | `manifest.json` | whether two bundles carry the same heritage |
| `repository_url` | `manifest.json` | where the claim can be verified |
| `artifact_count`, `format_version` | `manifest.json` | what shape the archive has |

A recipient who can reach the repository regenerates and compares
`content_hash`; identical means current, whatever the dates. **A recipient who
cannot reach it cannot decide**, and should say so rather than assume — FDN-0003
Article 12 applied to the projection itself.

*Two bundles of the same heritage built from different working trees are the
same projection: measured 2026-08-14, the 1 August bundle and the 14 August one
shared 80 of their 81 artifact identities, the single difference being a README
fixed in between.*

**The automated transfer has never run in the governed tree**, measured
2026-08-27 and stated here so this section is not read as describing a live
path: `SshBundleTransfer` is configured by `config/context_bundle_transfer.yml`,
which does not exist — only `context_bundle_transfer.yml.example` does — so the
export skips the transfer block entirely. That is the configuration rule working
as intended, and it means every bundle handed over so far left by a route this
procedure does not describe.

*Written on the owner's decision of 2026-08-28, and the risk was named before
it was taken: writing a procedure for something that has never run is what
produced W-07 of the 2026-08-13 boot report and the `PipelineRegistry` that
ARCH-0007 announced for a month after it was deleted. The mitigation is the
paragraph above — the section says what is verifiable and says which part does
not run.*

---

## Publishing an image

An image is not the heritage. It is a **build of one commit of it**, and this
section exists so that a published image can be traced back to that commit by
someone who has only the image.

**Why the procedure comes before the publication, and not after.** The last
image this project published — `aistack-core:0.1.0`, 2026-08-19 — was built
without one, carried bytecode the heritage did not know about, and was
**deleted rather than rebuilt** on 2026-08-23. `GOV-0002/OS-011` records the
argument the owner closed it with:

> *A rebuilt image would have to be verified before publication and then stay
> verified; an image nobody pulls cannot diverge from the heritage that
> describes it.*

**Publishing again reopens exactly that condition.** What makes it acceptable is
not that the defect was fixed — `.dockerignore` was corrected on 2026-08-21 —
but that the image now carries what it takes to check it.

### What is published, and what is not

**Only `aistack-core`**, the one-shot integrity validator built from
`Dockerfile`. Decided 2026-08-29 by the owner.

`selection-ui` is **not** published, for two measured reasons rather than one:
`Dockerfile.selection-ui` installs `fastapi`, `uvicorn`, `jinja2` and
`python-multipart`, none of which `pyproject.toml` declares — **the image
declares dependencies the heritage does not** — and the Selection UI is entering
redevelopment, so a *stable* tag would name a version already being replaced.

### The order

An image is built **after** the heritage is published, never before. The commit
it names must already be reachable in the SPOT, or the label points at nothing
a recipient can fetch.

```bash
test -z "$(git status --porcelain)" \
  && test "$(git rev-parse --abbrev-ref HEAD)" = main \
  && git fetch origin \
  && test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" \
  && source scripts/dev-env.sh \
  && pytest -q \
  && python3 -m aistack.cli.knowledge_integrity
```

Four terms, and each refuses a different way of publishing something nobody can
check: a dirty tree makes the label a lie; a branch other than `main` publishes
what the SPOT does not carry; **a `HEAD` ahead of `origin/main` names a commit
no recipient can fetch**; and a red suite or a blocking finding publishes a
state this heritage says is unsound.

**Before building a new version, every image `docker-compose.yml` still
lists as current is re-verified against its own recorded digest** —
`GOV-0002/OS-047`, decided 2026-09-04: a rebuilt image would have to be
verified before publication and then stay verified, and this is what
"stay verified" means in practice for a heritage with no registry
watching on its own. Not a scheduled check — a manual one, run as part of
the next publication rather than as standing infrastructure for a risk
that has not been observed (`ARC-P-006`):

```bash
for tag in 0.4.0 0.3.0; do
  docker pull "bigbrother1969/aistack-core:$tag"
  docker inspect --format '{{index .RepoDigests 0}}' \
    "bigbrother1969/aistack-core:$tag"
  # compare the printed digest against the one recorded for that tag
  # in docker-compose.yml — a mismatch is the divergence OS-047 named
done
```

A mismatch is investigated before the new version is pushed, not after.
Between two publications the exposure OS-047 named stays open and
undetected — accepted, at this heritage's current scale and audience,
rather than built against.

Then, from the repository directory:

```bash
VERSION="$(python3 -c 'import tomllib,pathlib; print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])')"

docker build -f Dockerfile \
  --label org.opencontainers.image.source="https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack" \
  --label org.opencontainers.image.revision="$(git rev-parse HEAD)" \
  --label org.opencontainers.image.version="$VERSION" \
  --label org.opencontainers.image.licenses="AGPL-3.0-or-later" \
  --label org.opencontainers.image.description="AIStack Knowledge Integrity validator" \
  -t "bigbrother1969/aistack-core:$VERSION" .

docker push "bigbrother1969/aistack-core:$VERSION"
```

**The version is read, not typed.** `pyproject.toml` declares it once and
`src/aistack/__main__.py` reads it from the installed metadata; a number typed
into a build command would be a third declaration, and the one that drifts
silently because nothing runs it twice.

**No credential appears here.** The owner authenticates to the registry
personally, as for every other step of this procedure.

### How a recipient checks an image

This is the part `OS-011` said was missing, and it is three commands:

```bash
docker inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' \
  bigbrother1969/aistack-core:<version>

git -C <clone> cat-file -t <that revision>          # the commit exists in the SPOT
git -C <clone> log -1 --format=%H <that revision>   # and this is what it is
```

**What that establishes and what it does not.** It establishes which commit the
image was built from, and that the commit is real. **It does not establish that
the image contains that commit's bytes** — a label is metadata, and anyone who
can build an image can write any label into it. The guarantee is the procedure,
not the label: the four terms above are what make the label true, and they run
on the owner's machine under his hand.

*Stated rather than implied, because the opposite reading is available and
comfortable: a label that looks like a checksum invites being read as one.*

### What is watched, and what is not

`tests/unit/test_the_image_declares_what_it_ships.py` guards the two conditions
that produced `OS-011`: that `.dockerignore` excludes bytecode **anywhere** in
the build context rather than only at its root, and that `Dockerfile` sets
`PYTHONDONTWRITEBYTECODE`. Both were true on 2026-08-29 and neither was watched
by anything until then.

**Nothing verifies a published image continuously**, and no test can: the
suite has no registry, and a check receives a projection rather than a
network — the same boundary § *The Context Bundle, and handing one over*
draws for bundles. What the heritage can do is refuse to build from a state
it calls unsound, and say what it did not check.

**Narrowed 2026-09-04 — `GOV-0002/OS-047`.** "Nothing verifies" was true of
every image published before this date and stays true between
publications: this section's own claim is not rewritten, because
continuous, unattended verification is still absent and still not built.
What changed is § *The order*, above — the previous image is re-verified
by hand immediately before the next one is built, so a published image is
checked at least once more after publication, not only at the moment it
was pushed.

### Recording the publication

The publication is recorded in `docker-compose.yml`, beside the service, **with
the digest and not only the tag** — a tag is a label someone can move, and a
digest is the image. The comment already carries that shape for the 0.1.0
publication, and it is kept: a record of what was published and then deleted is
what lets `OS-011` be read as something that happened rather than something
asserted.

### Recording what's new

**Narrowed 2026-09-04 — `GOV-0002/OS-055`.** `docker-compose.yml`'s record
proves what a build *is* — the digest, the commit, the test count. It says
nothing to a reader who has not already learned this heritage's own
vocabulary, and until `0.5.0` nothing else said it either: five published
versions, no readable account of what any of them changed.

Before, or alongside, bumping `pyproject.toml`'s version, an entry is
written to `docs/03-handbook/RELEASE-NOTES.md` (`RELEASE-NOTES`) — what
changed, in plain language, for someone who has not read this procedure.
The section at the foot of that document, naming what AIStack does taken
as a whole, is revised in the same pass whenever a version adds or changes
a capability.

This is a required step of publishing a version, the same standing as
§ *Recording the publication* above for the image — watched by
convention, not by an automated check, for the same reason: whether a
release note was written is not a fact a check can read off the
repository, only that one exists somewhere or does not.

---

## What is deliberately not here

- **Which machine holds which role**, and the addresses they use. Deployment
  configuration (GOV-0002/OS-015).
- **The infrastructure that publishes the SPOT to the public internet.** It
  serves the owner's wider environment and is not part of AIStack.
- **Credentials.** No token, password or key belongs in this heritage, and
  the owner authenticates every step personally.
