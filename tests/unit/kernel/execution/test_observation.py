from aistack.kernel.execution import (
    Observation,
    ObservationContext,
)


def context(component: str) -> ObservationContext:
    return ObservationContext(
        request_id="request-001",
        component_type="task",
        component_id=component,
        operation="execute",
    )


def test_atomic_observation() -> None:
    observation = Observation(
        context=context("atomic"),
    )

    assert observation.is_atomic
    assert observation.children == ()


def test_recursive_observation() -> None:
    child = Observation(
        context=context("child"),
    )

    parent = Observation(
        context=context("parent"),
        children=(child,),
    )

    assert not parent.is_atomic
    assert len(parent.children) == 1
