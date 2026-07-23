from pathlib import Path


def test_runtime_does_not_depend_on_task_registry() -> None:
    runtime_path = Path("src/aistack/kernel/runtime")

    for source_file in runtime_path.glob("*.py"):
        content = source_file.read_text()

        assert "TaskRegistry" not in content
