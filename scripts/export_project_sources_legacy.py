#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "context" / "bundles"
OUT_MD = OUT_DIR / "AIStack-Project-Sources.md"
OUT_ZIP = OUT_DIR / "AIStack-Project-Sources.zip"

MANDATORY_FILES = [
    ROOT / "context" / "README_AI.md",
    ROOT / "context" / "AI_PROTOCOL.md",
    ROOT / "context" / "AI_TRANSACTION_PROTOCOL.md",
    ROOT / "docs" / "99-meta" / "NEXT-SESSION-TODO.md",
]

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "archive",
    "reports",
    "exports",
    "__pycache__",
    "context/bundles",
}


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def is_included(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path.relative_to(ROOT.parent)
    rel_posix = rel.as_posix()
    return not any(part in rel.parts or rel_posix.startswith(part + "/") for part in EXCLUDED_PARTS)


def add_file(files: list[Path], path: Path) -> None:
    if path.exists() and is_included(path) and path not in files:
        files.append(path)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    missing = [str(path.relative_to(ROOT)) for path in MANDATORY_FILES if not path.exists()]
    if missing:
        raise SystemExit("Missing mandatory Context Bundle files:\n" + "\n".join(f"- {m}" for m in missing))

    branch = git_value("rev-parse", "--abbrev-ref", "HEAD")
    commit = git_value("rev-parse", "--short", "HEAD")
    generated = datetime.now().isoformat(timespec="seconds")

    files: list[Path] = []

    add_file(files, ROOT / "README.md")
    for path in MANDATORY_FILES:
        add_file(files, path)

    for path in sorted((ROOT / "docs").rglob("*.md")):
        add_file(files, path)

    book_repo = ROOT.parent / "la-politique-de-l-autruche"
    if book_repo.exists():
        for path in sorted((book_repo / "methodology").rglob("*.md")):
            add_file(files, path)

    parts = [
        "# AIStack Project Sources",
        "",
        "Generated artifact — DO NOT EDIT.",
        "",
        f"- Branch: {branch}",
        f"- Commit: {commit}",
        f"- Generated: {generated}",
        "",
        "---",
        "",
    ]

    for path in files:
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            rel = path.relative_to(ROOT.parent)
        parts.append(f"# Source: `{rel}`")
        parts.append("")
        parts.append(path.read_text(encoding="utf-8"))
        parts.append("")
        parts.append("---")
        parts.append("")

    OUT_MD.write_text("\n".join(parts), encoding="utf-8")

    if OUT_ZIP.exists():
        OUT_ZIP.unlink()

    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(OUT_MD, OUT_MD.name)
        for path in files:
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = Path("external") / path.relative_to(ROOT.parent)
            z.write(path, rel.as_posix())

    print(f"Generated: {OUT_MD}")
    print(f"Generated: {OUT_ZIP}")


if __name__ == "__main__":
    main()
