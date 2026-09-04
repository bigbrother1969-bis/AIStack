from dataclasses import dataclass


@dataclass(frozen=True)
class CorrelatedFinding:
    """
    One container's own evidence, from three independent sources,
    each carrying where it was read.

    `STD-0300` § VS-4 criterion 4.2: "the finding correlates process,
    container and deployment definition, each with an observation
    reference." Three fields, three references — this is that
    statement, typed:

    - `container_command` / `container_reference` — what Docker
      recorded the container was configured to run
      (`docker ps --no-trunc`, the same read `find_development_flags`
      already uses for 4.3).
    - `process_command` / `process_reference` — what is actually
      running inside the container's own PID namespace right now
      (`docker top <container>`). Independent of the first: a
      container's configured command and its live process can
      diverge — a shell wrapper, a supervisor, a process that
      re-executed itself with different arguments.
    - `deployment_command` / `deployment_reference` — what the
      artifact that built this container declared it should run.
      `None` for both is a real, declared state, not a gap this type
      hides: most of this deployment's containers are not defined by
      anything this repository can read (`ARC-P-013`'s boundary
      applies to knowledge this heritage governs, not to a personal
      stack deployed and managed entirely outside it), and `GOV-P-001`
      forbids inventing a source that was not stated.
    """

    container: str
    container_command: str
    container_reference: str
    process_command: str
    process_reference: str
    deployment_command: str | None
    deployment_reference: str | None

    def __post_init__(self) -> None:
        if not self.container.strip():
            raise ValueError(
                "a correlated finding is about one container; this "
                "one names none"
            )

        if (self.deployment_command is None) != (self.deployment_reference is None):
            raise ValueError(
                f"{self.container}: deployment_command and "
                f"deployment_reference must be declared together, or "
                f"neither at all — a command with no reference is "
                f"unverifiable, and a reference to nothing is empty"
            )
