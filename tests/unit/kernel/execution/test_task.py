from aistack.kernel.execution import (
    Observation,
    ObservationContext,
    Request,
)


class DummyTask:
    task_id = "dummy"
    task_name = "Dummy Task"

    def execute(self, request: Request) -> Observation:
        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
        )


def test_dummy_task_execution() -> None:
    task = DummyTask()

    request = Request(
        request_id="request-001",
        task_id="dummy",
    )

    observation = task.execute(request)

    assert observation.context.request_id == request.request_id
    assert observation.context.component_id == "dummy"
