from __future__ import annotations

from pathlib import Path

from aistack.generators.docker import DockerKnowledgeAssetGenerator
from aistack.knowledge.docker import DockerKnowledgeAssetBuilder
from aistack.providers.docker import DockerProvider


def main() -> None:
    observation = DockerProvider().collect()
    asset = DockerKnowledgeAssetBuilder().build(observation)

    output_path = DockerKnowledgeAssetGenerator().generate(
        asset=asset,
        output_path=Path("reports/generated/docker-knowledge-assets.json"),
    )

    print(f"Docker Knowledge Assets written to {output_path}")


if __name__ == "__main__":
    main()
