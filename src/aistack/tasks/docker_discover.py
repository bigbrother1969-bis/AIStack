from __future__ import annotations

from pathlib import Path

from aistack.generators.docker import DockerObservationArtifactGenerator
from aistack.kernel.contracts import KnowledgeProvider
from aistack.kernel.execution import Observation, ObservationContext, Request


DEFAULT_OUTPUT_PATH = "reports/generated/docker-provider-observation.json"


class DockerDiscoverTask:
    """
    Collect Docker observations and write them as an artifact.

    Calls the provider's `collect()`, then the generator, writing to the
    request payload's `output_path` (default `DEFAULT_OUTPUT_PATH`).
    Returns an Observation carrying the written path.
    """

    task_id = "docker.discover"
    task_name = "Docker Discover"

    def __init__(
        self,
        provider: KnowledgeProvider,
        generator: DockerObservationArtifactGenerator | None = None,
    ) -> None:
        self._provider = provider
        self._generator = generator or DockerObservationArtifactGenerator()

    def execute(self, request: Request) -> Observation:
        output_path = Path(
            request.payload.get("output_path", DEFAULT_OUTPUT_PATH)
        )

        raw_observation = self._provider.collect()

        written_path = self._generator.generate(
            observation=raw_observation,
            output_path=output_path,
        )

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={"output_path": str(written_path)},
        )
