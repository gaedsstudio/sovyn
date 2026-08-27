import re
import shutil
from pathlib import Path

CHECKPOINT_PATTERN = re.compile(r"^checkpoint-(?P<step>\d+)$")


def checkpoint_step(path: Path) -> int | None:
    match_result = CHECKPOINT_PATTERN.match(path.name)
    if match_result is None:
        return None
    return int(match_result.group("step"))


def cleanup_checkpoints(checkpoint_dir: Path, keep: int = 2) -> list[Path]:
    checkpoints = [
        (step, path)
        for path in checkpoint_dir.glob("checkpoint-*")
        if path.is_dir()
        for step in [checkpoint_step(path)]
        if step is not None
    ]
    checkpoints.sort(key=lambda item: item[0])
    stale = checkpoints[: max(0, len(checkpoints) - keep)]
    removed: list[Path] = []
    for _step, path in stale:
        shutil.rmtree(path)
        removed.append(path)
    return removed


def cleanup_temporary_files(output_root: Path) -> list[Path]:
    removed: list[Path] = []
    for path in output_root.rglob("*"):
        if path.is_file() and path.suffix == ".tmp":
            path.unlink()
            removed.append(path)
    tmp_dir = output_root / "tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
        removed.append(tmp_dir)
    return removed
