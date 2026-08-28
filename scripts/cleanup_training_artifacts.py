from pathlib import Path
import shutil

TARGETS = (
    Path("outputs"),
    Path("checkpoints"),
    Path("ml/outputs"),
    Path("ml/checkpoints"),
)


def main() -> int:
    removed = 0
    for target in TARGETS:
        if target.exists():
            shutil.rmtree(target)
            removed += 1
    print(f"Removed {removed} generated training artifact directories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

