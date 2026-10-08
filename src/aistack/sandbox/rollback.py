"""
Rollback rehearsal (`ADR-0018`, 1.9 — owner's decision 2026-10-08):
before going back to the image a service ran before its last upgrade,
rehearse it in the sandbox — the latest backup restored with that
earlier image, checked like any restore — and print the line to pin
in the service's compose file. Going back for real stays the owner's
act.

"The image before" is read from the digest collector's own history
(`docker-digest/<project>/<service>/history/`): the newest recorded
digest that differs from the one the container runs now. When that
image is no longer on the host (a Watchtower clean-up), it is fetched
again by the registry digest the collector records since 1.9; an
earlier record has none, and the report says the image cannot be
fetched.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from aistack.providers.docker.identity import stable_subject_from_labels
from aistack.sandbox.declaration import SandboxRecipe
from aistack.sandbox.run import SandboxRun, StepFailed

_LABELS = (
    "com.docker.compose.project",
    "com.docker.compose.service",
    "com.docker.compose.project.working_dir",
    "com.docker.compose.project.config_files",
)


@dataclass(frozen=True)
class PreviousImage:
    container: str
    subject: str
    image_name: str
    current: str
    previous: str
    upgraded_at: str
    repo_digests: tuple[str, ...] = ()
    compose_dir: str = ""
    compose_files: str = ""
    compose_service: str = ""
    # Filled once the image is on the host: what the sandbox starts.
    used: str = field(default="", compare=False)


def recipe_containers(recipe: SandboxRecipe) -> list[str]:
    return [name for name in (recipe.live_database_container, recipe.live_web_container) if name]


def _value(text: str) -> str:
    return "" if text in ("<no value>", "") else text


def find_previous(run: SandboxRun, container: str, generated_dir: Path) -> PreviousImage | None:
    """The image `container` ran before its last recorded upgrade, or
    None when the history holds no earlier digest."""

    fields = "|".join(["{{.Image}}", "{{.Config.Image}}"] + [f'{{{{index .Config.Labels "{label}"}}}}' for label in _LABELS])
    shown = run.docker("inspect", "--format", fields, container).stdout.strip().split("|")
    if len(shown) < 2 + len(_LABELS):
        raise StepFailed(f"cannot read the live container {container}")
    current, image_name = shown[0], shown[1]
    labels = {label: _value(value) for label, value in zip(_LABELS, shown[2:], strict=True)}
    subject = stable_subject_from_labels(labels, name=container)

    history = generated_dir / "docker-digest" / subject / "history" / "docker-digest"
    records = sorted(history.glob("*.json")) if history.is_dir() else []
    upgraded_at = ""
    for path in reversed(records):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        digest = record.get("digest") if isinstance(record, dict) else None
        if not isinstance(digest, str):
            continue
        if digest == current:
            upgraded_at = path.stem
            continue
        return PreviousImage(
            container=container,
            subject=subject,
            image_name=str(record.get("image") or image_name),
            current=current,
            previous=digest,
            upgraded_at=upgraded_at,
            repo_digests=tuple(str(item) for item in record.get("repo_digests") or ()),
            compose_dir=labels["com.docker.compose.project.working_dir"],
            compose_files=labels["com.docker.compose.project.config_files"],
            compose_service=labels["com.docker.compose.service"],
        )
    return None


def _repository(image_name: str) -> str:
    """`wordpress:latest` → `wordpress`; `ghcr.io/x/y:v2` → `ghcr.io/x/y`."""

    name = image_name.split("@", 1)[0]
    last = name.rsplit("/", 1)[-1]
    return name[: len(name) - len(last)] + last.split(":", 1)[0]


def _matching_repo_digest(previous: PreviousImage) -> str:
    repository = _repository(previous.image_name)
    for candidate in previous.repo_digests:
        if candidate.split("@", 1)[0] == repository:
            return candidate
    return previous.repo_digests[0] if previous.repo_digests else ""


def make_available(run: SandboxRun, previous: PreviousImage) -> str:
    """The reference the sandbox can start: the local image when it is
    still on the host, else the registry digest, pulled."""

    if run.docker_try("image", "inspect", "--format", "{{.Id}}", previous.previous).returncode == 0:
        return previous.previous
    reference = _matching_repo_digest(previous)
    if not reference:
        raise StepFailed(
            f"the image {previous.container} ran before ({previous.previous[:19]}…) is no longer on this host, "
            "and no registry digest was recorded for it (recorded before the digest collector kept them): "
            "it cannot be fetched again"
        )
    run.progress(f"    docker pull {reference}")
    run.docker("pull", reference, timeout=1800)
    return reference


def prepare_rollback(
    run: SandboxRun,
    recipe: SandboxRecipe,
    generated_dir: Path,
    only: str = "",
) -> list[PreviousImage]:
    """Find, fetch if needed, and set the earlier images the restore
    will start. Raises `StepFailed` when none can be rehearsed."""

    containers = recipe_containers(recipe)
    if only:
        if only not in containers:
            raise StepFailed(f"{only} is not a container of the {recipe.name} recipe ({', '.join(containers)})")
        containers = [only]

    found: list[PreviousImage] = []
    with run.step("previous images"):
        unchanged = []
        for container in containers:
            previous = find_previous(run, container, generated_dir)
            if previous is None:
                unchanged.append(container)
            else:
                found.append(previous)
        run.facts["rollback"] = {"no_earlier_image": unchanged}
        if not found:
            raise StepFailed(
                "no earlier image recorded for " + ", ".join(unchanged)
                + " — the digest collector has seen no upgrade of it"
            )

    with run.step("fetch previous images"):
        ready = []
        for previous in found:
            used = make_available(run, previous)
            ready.append(PreviousImage(**{**previous.__dict__, "used": used}))
            run.image_overrides[previous.container] = used
        run.facts["rollback"]["images"] = {
            item.container: {
                "subject": item.subject, "current": item.current, "previous": item.previous,
                "upgraded_at": item.upgraded_at, "started": item.used,
                "repo_digest": _matching_repo_digest(item),
            }
            for item in ready
        }
    return ready


def pin_instructions(previous: PreviousImage) -> list[str]:
    """What the owner copies to go back for real: the compose line to
    pin, and the command to apply it."""

    lines = [f"{previous.container} ({previous.subject}) :"]
    reference = _matching_repo_digest(previous)
    if reference:
        pinned = reference
    else:
        pinned = f"{_repository(previous.image_name)}:rollback"
        lines.append(f"  docker tag {previous.previous} {pinned}")
    where = previous.compose_files or (f"{previous.compose_dir}/docker-compose.yml" if previous.compose_dir else "")
    lines.append(f"  dans {where or 'son fichier compose'}, service {previous.compose_service or previous.container} :")
    lines.append(f"    image: {pinned}")
    if previous.compose_dir and previous.compose_service:
        lines.append(f"  cd {previous.compose_dir} && docker compose up -d {previous.compose_service}")
    lines.append("  (une image épinglée par son digest n'est plus mise à jour par Watchtower : retire l'épingle une fois le problème réglé)")
    return lines
