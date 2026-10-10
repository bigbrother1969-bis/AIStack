from __future__ import annotations

import json
import subprocess

from typing import Any

from aistack.providers.docker.identity import identities_of, list_running_container_names

# Digest drift: a running container whose `ContainerIdentity.image_digest`
# differs from the last one recorded for the same `aistack:stableSubject`
# is local proof of an upgrade, with no registry call. Running containers
# only, like `collect_running_container_diffs`.


def collect_running_container_digests() -> list[dict[str, Any]]:
    """One cycle: `{"subject", "digest", "image"}` for each running container.

    A container that stopped between `docker ps` and `docker inspect` is
    absent. An empty `image_digest` is skipped: it is a missing value, not
    an observation to compare against.
    """

    names = list_running_container_names()
    identities = identities_of(names)

    results: list[dict[str, Any]] = []
    for identity in identities:
        if not identity.image_digest:
            continue
        results.append({
            "subject": identity.stable_subject,
            "digest": identity.image_digest,
            "image": identity.image_name,
        })

    return results


def image_repo_digests(image_id: str) -> list[str]:
    """Registry digests (`repo@sha256:…`) of one local image.

    Unlike the local id, these can be pulled again after the image is
    removed, e.g. by a Watchtower clean-up (`ADR-0018`, rollback by
    digest). Empty when Docker does not answer or the image was never
    pushed.
    """

    try:
        done = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", image_id],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if done.returncode != 0:
        return []
    try:
        parsed = json.loads(done.stdout.strip() or "[]")
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []
