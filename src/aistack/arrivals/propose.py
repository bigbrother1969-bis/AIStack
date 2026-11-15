"""The declaration to propose for what arrived: text the owner reads and may accept."""

from __future__ import annotations

import json
import re


def suggested_name(container: str) -> str:
    """`stable-diffusion_ui` becomes `Stable Diffusion Ui`: a name to correct, not a guess at the product."""

    words = [word for word in re.split(r"[-_.\s]+", container) if word]

    return " ".join(word[:1].upper() + word[1:] for word in words) or container


def suggested_description(image: str | None, ports: str | None, gpu: bool) -> str:
    parts = [part for part in (image, ports) if part]

    if gpu:
        parts.append("GPU")

    return " — ".join(parts)


def service_lines(indent: str, name: str, container: str, description: str) -> list[str]:
    """One service of `service_categorization.yml`; every value quoted, so no character can break the file."""

    lines = [f"{indent}- name: {json.dumps(name, ensure_ascii=False)}"]
    lines.append(f"{indent}  container: {json.dumps(container, ensure_ascii=False)}")

    if description.strip():
        lines.append(f"{indent}  description: {json.dumps(description.strip(), ensure_ascii=False)}")

    return lines


def host_block(address: str, user: str | None) -> str:
    """What to add to `hosts.yml` once the collector runs on that machine (ADR-0020)."""

    name = "machine-" + address.rsplit(".", 1)[-1]
    block = f"hosts:\n  {name}:\n    directory: hosts/{name}\n    address: {address}\n"

    return block if not user else f"# ssh {user}@{address}\n{block}"
