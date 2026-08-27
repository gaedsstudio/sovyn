from pathlib import Path

import pytest

from sovyn_training.errors import DiskSpaceError
from sovyn_training.tools.checkpoints import cleanup_checkpoints
from sovyn_training.tools.storage import (
    DiskEstimate,
    build_storage_report,
    check_disk_space,
    directory_size,
    estimate_disk_usage,
)


def test_checkpoint_cleanup_when_more_than_two_exist(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "checkpoints"
    for step in (100, 200, 300):
        (checkpoint_dir / f"checkpoint-{step}").mkdir(parents=True)

    removed = cleanup_checkpoints(checkpoint_dir, keep=2)

    assert [path.name for path in removed] == ["checkpoint-100"]
    assert sorted(path.name for path in checkpoint_dir.iterdir()) == [
        "checkpoint-200",
        "checkpoint-300",
    ]


def test_storage_report_when_files_are_separated(tmp_path: Path) -> None:
    model_cache = tmp_path / "hf-cache"
    dataset = tmp_path / "data"
    adapters = tmp_path / "adapters"
    checkpoints = tmp_path / "checkpoints"
    logs = tmp_path / "logs"
    for directory in (model_cache, dataset, adapters, checkpoints, logs):
        directory.mkdir()
        (directory / "file.txt").write_text("12345", encoding="utf-8")

    report = build_storage_report(model_cache, dataset, adapters, checkpoints, logs)

    assert report.base_model_cache_bytes == 5
    assert report.sovyn_bytes == 20
    assert report.total_bytes == 25


def test_disk_estimate_when_multiplier_is_used() -> None:
    estimate = estimate_disk_usage(
        model_size_bytes=1_000_000_000,
        dataset_size_bytes=100_000_000,
        multiplier=1.25,
    )

    assert estimate.required_bytes > 1_100_000_000
    assert estimate.checkpoint_bytes == estimate.adapter_bytes * 2


def test_disk_guard_when_requirement_exceeds_available(tmp_path: Path) -> None:
    estimate = DiskEstimate(
        base_model_bytes=10**18,
        dataset_bytes=0,
        adapter_bytes=0,
        checkpoint_bytes=0,
        temporary_bytes=0,
        multiplier=1.0,
    )

    with pytest.raises(DiskSpaceError):
        check_disk_space(tmp_path, estimate)


def test_directory_size_when_path_is_missing(tmp_path: Path) -> None:
    assert directory_size(tmp_path / "missing") == 0
