from pathlib import Path
import shutil

REPO_ROOT = Path(__file__).resolve().parents[2]
INBOX = REPO_ROOT / "inbox" / "knowledge"


def target_for(file: Path) -> Path | None:
    name = file.name.lower()

    if name.startswith("adr-") and name.endswith(".md"):
        return REPO_ROOT / "docs" / "adr" / file.name

    return None


def main() -> None:
    imported = 0
    skipped = 0

    INBOX.mkdir(parents=True, exist_ok=True)

    for file in sorted(INBOX.iterdir()):
        if not file.is_file():
            continue

        target = target_for(file)

        if target is None:
            print(f"SKIP unsupported artifact: {file.name}")
            skipped += 1
            continue

        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            print(f"SKIP already exists: {target}")
            skipped += 1
            continue

        shutil.move(str(file), str(target))
        print(f"IMPORTED {file.name} -> {target}")
        imported += 1

    print(f"Import complete: {imported} imported, {skipped} skipped")


if __name__ == "__main__":
    main()
