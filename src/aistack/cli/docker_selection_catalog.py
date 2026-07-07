from __future__ import annotations

import json
from pathlib import Path

from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.kernel.bootstrap import create_kernel_context
from aistack.selection.from_docker_catalog import DockerSelectionCatalogBuilder


def main() -> None:
    ctx = create_kernel_context()
    observation = ctx.providers.get("docker").collect()
    docker_catalog = DockerRuntimeCatalogBuilder().build(observation)
    selection_catalog = DockerSelectionCatalogBuilder().build(docker_catalog)

    output_path = Path("reports/generated/docker-selection-catalog.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(selection_catalog, default=lambda item: item.__dict__, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Docker selection catalog written to {output_path}")


if __name__ == "__main__":
    main()
