from __future__ import annotations

import json
import subprocess

from typing import Any

from aistack.providers.docker.identity import identities_of, list_running_container_names

# 1.5's third collector (dérive du digest), cadrage 2026-09-28 —
# ordered after `docker diff` (decision 3, `aistack.providers.docker
# .diff`'s own module comment) as the roadmap's own § 1.5 "l'image
# avant/après" need: a running container whose own `ContainerIdentity
# .image_digest` (`aistack.providers.docker.identity`'s own comment
# explains exactly which digest that is, and why) differs from the
# last one recorded for the same `aistack:stableSubject` is the local
# proof an upgrade happened, with no registry call on either side —
# decision 4, confirmed 2026-09-27 alongside the cadrage for the two
# remaining collectors, before either was built.
#
# **Running containers only**, the same restriction `collect_running
# _container_diffs` already holds (decision 1 of that module's own
# comment) and for the same reason: a stopped container's own image
# reference is not drifting under active use, and this collector has
# nothing further to add for one Docker itself is not currently
# running.
#
# **No separate module for the `docker inspect` call itself** — unlike
# `aistack.providers.docker.diff`, which wraps its own `docker diff`
# subprocess, this collector has nothing left to wrap: the one fact it
# needs (`.Image`) is already resolved by `identities_of`, the shared
# module built the same day `docker diff` was, precisely so this
# collector and the one still to come (inventaire des paquets) would
# not each need their own copy of the same `docker inspect` shape.


def collect_running_container_digests() -> list[dict[str, Any]]:
    """
    One cycle: every running container's own stable identity (§ 3)
    paired with its own current image digest —
    `{"subject": ..., "digest": ...}` per container `docker inspect`
    could still resolve at the moment this ran (`identities_of`'s own
    contract, the same race `collect_running_container_diffs` already
    documents: a container that stopped between `docker ps` and here
    is simply absent, never an error).

    An identity whose own `image_digest` came back empty (`docker
    inspect` reported no `.Image` at all — not observed in practice on
    this project's own hosts, but `ContainerIdentity`'s own default
    allows it) is skipped rather than recorded as an empty string: an
    empty digest is not a real observation of "no image", it is the
    absence of one, and `aistack.providers.docker.digest_history`'s
    own write-on-change contract has nothing meaningful to compare an
    empty value against.
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
    """
    The registry digests (`repo@sha256:…`) of one local image — what
    `docker pull` can fetch again once the image itself has been
    removed (a Watchtower clean-up), which the local id cannot
    (`ADR-0018`, rollback by digest, 1.9). Empty when Docker does not
    answer, or for an image built locally and never pushed.
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
