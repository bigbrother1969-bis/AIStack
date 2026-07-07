#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "context" / "bundles"
OUT_MD = OUT_DIR / "AIStack-Project-Sources.md"
OUT_ZIP = OUT_DIR / "AIStack-Project-Sources.zip"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "archive",
    "reports",
    "exports",
    "__pycache__",
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
    return not any(part in EXCLUDED_PARTS for part in rel.parts)

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    branch = git_value("rev-parse", "--abbrev-ref", "HEAD")
    commit = git_value("rev-parse", "--short", "HEAD")
    generated = datetime.now().isoformat(timespec="seconds")

    files = []
    files.append(ROOT / "README.md")
    files.extend(sorted((ROOT / "docs").rglob("*.md")))

    book_repo = ROOT.parent / "la-politique-de-l-autruche"
    if book_repo.exists():
        files.extend(sorted((book_repo / "methodology").rglob("*.md")))

    files = [p for p in files if p.exists() and is_included(p)]

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

    print(f"Generated: {OUT_MD}")
    print(f"Generated: {OUT_ZIP}")

if __name__ == "__main__":
    main()
