from aistack.kernel.execution import Observation, ObservationContext


def build_context(component_id: str) -> ObservationContext:
    return ObservationContext(
        request_id="request-001",
        component_type="task",
        component_id=component_id,
        operation="execute",
    )


def test_observation_without_children_is_atomic() -> None:
    observation = Observation(
        context=build_context("task.atomic"),
        data={"status": "observed"},
    )

    assert observation.is_atomic
    assert observation.children == ()


def test_observation_preserves_child_observations() -> None:
    child = Observation(
        context=build_context("task.child"),
        data={"value": 1},
    )

    parent = Observation(
        context=build_context("task.parent"),
        children=(child,),
    )

    assert not parent.is_atomic
    assert parent.children == (child,)
