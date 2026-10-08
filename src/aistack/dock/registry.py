"""
The digest a registry publishes for an image tag, now (`ADR-0019` § 1):
what `docker pull <tag>` would fetch, asked without pulling anything —
one `HEAD` on the manifest, with the anonymous token the registry hands
out for public images (Docker Hub, GitHub's registry, any registry that
answers a 401 with a Bearer challenge).
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

DOCKER_HUB = "registry-1.docker.io"

_ACCEPT = ", ".join((
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
))


@dataclass(frozen=True)
class ImageReference:
    registry: str
    repository: str
    tag: str

    @property
    def short_repository(self) -> str:
        """The name `docker` itself shows in RepoDigests: `wordpress`
        for an official Docker Hub image, `ghcr.io/x/y` elsewhere."""

        if self.registry == DOCKER_HUB:
            return self.repository.removeprefix("library/")
        return f"{self.registry}/{self.repository}"


def parse_reference(image: str) -> ImageReference:
    """`wordpress:latest`, `mariadb:11`, `ghcr.io/immich-app/immich-server:v2.7.5`."""

    name = image.split("@", 1)[0]
    first, _, rest = name.partition("/")
    if rest and ("." in first or ":" in first or first == "localhost"):
        registry, path = first, rest
    else:
        registry, path = DOCKER_HUB, name
    last = path.rsplit("/", 1)[-1]
    tag = last.split(":", 1)[1] if ":" in last else "latest"
    repository = path[: len(path) - len(last)] + last.split(":", 1)[0]
    if registry == DOCKER_HUB and "/" not in repository:
        repository = f"library/{repository}"
    if registry == "docker.io":
        registry = DOCKER_HUB
    return ImageReference(registry, repository, tag)


Opener = Callable[[urllib.request.Request, float], tuple[int, dict[str, str], bytes]]


def _open(request: urllib.request.Request, timeout: float) -> tuple[int, dict[str, str], bytes]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:  # noqa: S310 - https registries only
            return answer.status, {k.lower(): v for k, v in answer.headers.items()}, answer.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, b""


def _challenge(header: str) -> dict[str, str]:
    return dict(re.findall(r'(\w+)="([^"]*)"', header))


def published_digest(image: str, *, opener: Opener = _open, timeout: float = 15) -> str:
    """The registry's current digest for `image`'s tag. Raises
    `LookupError` with the reason when the registry does not say."""

    reference = parse_reference(image)
    url = f"https://{reference.registry}/v2/{reference.repository}/manifests/{reference.tag}"
    headers = {"Accept": _ACCEPT}
    status, answer_headers, _ = opener(urllib.request.Request(url, method="HEAD", headers=headers), timeout)
    if status == 401:
        challenge = _challenge(answer_headers.get("www-authenticate", ""))
        realm = challenge.pop("realm", "")
        if not realm:
            raise LookupError(f"{reference.registry} asks for credentials this image's tag cannot be read without")
        challenge.setdefault("scope", f"repository:{reference.repository}:pull")
        token_status, _, body = opener(
            urllib.request.Request(f"{realm}?{urllib.parse.urlencode(challenge)}"), timeout
        )
        if token_status != 200:
            raise LookupError(f"{reference.registry} refused an anonymous token (HTTP {token_status})")
        token = json.loads(body or b"{}")
        bearer = token.get("token") or token.get("access_token") or ""
        headers["Authorization"] = f"Bearer {bearer}"
        status, answer_headers, _ = opener(urllib.request.Request(url, method="HEAD", headers=headers), timeout)
    digest = answer_headers.get("docker-content-digest", "")
    if status != 200 or not digest:
        raise LookupError(f"{reference.registry} gave no digest for {image} (HTTP {status})")
    return digest
