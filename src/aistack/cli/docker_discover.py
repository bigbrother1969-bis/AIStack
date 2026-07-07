from __future__ import annotations

from pathlib import Path

from aistack.generators.docker import DockerObservationArtifactGenerator
from aistack.providers.docker import DockerProvider


def main() -> None:
    observation = DockerProvider().collect()

    output_path = DockerObservationArtifactGenerator().generate(
        observation=observation,
        output_path=Path("reports/generated/docker-provider-observation.json"),
    )

    print(f"Docker observation written to {output_path}")


if __name__ == "__main__":
    main()
