from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionPhase:
    id: str
    name: str

    description: str = ""
    order: int = 0
