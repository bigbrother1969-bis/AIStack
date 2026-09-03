from __future__ import annotations

from pathlib import Path

from aistack.generators.docker import DockerObservationArtifactGenerator
from aistack.kernel.contracts import KnowledgeProvider
from aistack.kernel.execution import Observation, ObservationContext, Request


DEFAULT_OUTPUT_PATH = "reports/generated/docker-provider-observation.json"


class DockerDiscoverTask:
    """
    The first production Task the Kernel Runtime executes.

    **GOV-0002/OS-041 named exactly this move as the open work**:
    *"the dimension needs a first `Task` whose subject exists"* and
    *"the four provider CLIs are the candidates... turning one into
    a registered task is the measurement that would tell whether the
    abstraction earns itself."* This is that task, on that
    candidate — `docker_discover`, chosen for being the CLI with the
    least ceremony (one provider call, one generator call, no
    branching), so the first production `Request` traverses the
    Runtime rather than a case worth arguing about on its own terms.

    **Reopened, not reversed.** OS-041 resolved 2026-08-29 by
    declaring the Execution Dimension unearned, on ARC-P-006 — build
    the abstraction only once a real subject needs it. It named its
    own reopening condition: a first Task whose subject exists.
    2026-09-03's real subject is Observation History wanting a
    Runtime Operation History dimension to extend into — recording
    what AIStack executed, not only what it observed — which only
    means something once at least one execution is real. This task
    supplies that one execution. `PackageCapability`, `Action` and
    `Observation Service` — the half of ADR-0008's chain that could
    not be instantiated and was removed under the same principle —
    stay removed; nothing here resurrects them.

    **Wraps `docker_discover.py`'s prior logic unchanged, not
    rewritten.** Before this task existed, the CLI called
    `DockerProvider.collect()` and `DockerObservationArtifactGenerator
    .generate()` directly in `main()`. Both calls move here verbatim;
    what changes is who calls them — the Runtime instead of the CLI
    directly — which is the whole point of the measurement.
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
