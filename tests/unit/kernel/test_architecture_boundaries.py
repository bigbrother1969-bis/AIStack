from pathlib import Path


def test_runtime_does_not_depend_on_task_registry() -> None:
    runtime_path = Path("src/aistack/kernel/runtime")

    for source_file in runtime_path.glob("*.py"):
        content = source_file.read_text()

        assert "TaskRegistry" not in content


def _kernel_runtime_boot_calls(content: str) -> list[str]:
    """
    Extract the argument text of every `KernelRuntime.boot(...)`
    call found in `content`, parens balanced so a nested call (such
    as `FileTraceRepository()`) never truncates the scan early.
    """

    marker = "KernelRuntime.boot("
    calls: list[str] = []
    start = 0

    while True:
        index = content.find(marker, start)
        if index == -1:
            break

        depth = 1
        position = index + len(marker)
        while position < len(content) and depth > 0:
            if content[position] == "(":
                depth += 1
            elif content[position] == ")":
                depth -= 1
            position += 1

        calls.append(content[index + len(marker) : position - 1])
        start = position

    return calls


def test_every_kernel_runtime_boot_call_in_cli_declares_a_trace_repository() -> None:
    """
    Kernel Runtime tracing invariant, audited 2026-09-23
    (`claude/AUDIT-KERNEL-RUNTIME-CALLERS-2026-09-23.md`) —
    `KernelRuntime.boot()` falls back silently to
    `InMemoryTraceRepository()` for any caller that does not pass
    `trace_repository=` explicitly, and only
    `aistack.cli.docker_discover` does that today. Companion to
    `tests/unit/kernel/bootstrap/test_tasks.py::
    test_only_the_tasks_declared_here_are_registered`, which catches
    a second Task appearing — this one catches the other half: a CLI
    module that boots the Runtime without asking for durable
    tracing, an execution Runtime Operation History would never see.
    """

    cli_path = Path("src/aistack/cli")

    violations = [
        f"{source_file.name}: {call.strip()}"
        for source_file in cli_path.glob("*.py")
        for call in _kernel_runtime_boot_calls(source_file.read_text())
        if "trace_repository" not in call
    ]

    assert violations == []
