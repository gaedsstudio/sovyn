import shutil
from dataclasses import dataclass
from pathlib import Path

from sovyn_training.errors import DiskSpaceError, MergeExportError

BYTES_PER_UNIT = 1024.0


@dataclass(frozen=True, slots=True)
class StorageReport:
    base_model_cache_bytes: int
    dataset_bytes: int
    adapters_bytes: int
    checkpoints_bytes: int
    logs_bytes: int

    @property
    def sovyn_bytes(self) -> int:
        return (
            self.dataset_bytes
            + self.adapters_bytes
            + self.checkpoints_bytes
            + self.logs_bytes
        )

    @property
    def total_bytes(self) -> int:
        return self.base_model_cache_bytes + self.sovyn_bytes


@dataclass(frozen=True, slots=True)
class DiskEstimate:
    base_model_bytes: int
    dataset_bytes: int
    adapter_bytes: int
    checkpoint_bytes: int
    temporary_bytes: int
    multiplier: float

    @property
    def required_bytes(self) -> int:
        subtotal = (
            self.base_model_bytes
            + self.dataset_bytes
            + self.adapter_bytes
            + self.checkpoint_bytes
            + self.temporary_bytes
        )
        return int(subtotal * self.multiplier)


@dataclass(frozen=True, slots=True)
class DiskGuardResult:
    available_bytes: int
    required_bytes: int

    @property
    def safe_to_start(self) -> bool:
        return self.available_bytes >= self.required_bytes


def directory_size(path: Path | None) -> int:
    if path is None or not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def build_storage_report(
    model_cache: Path | None,
    dataset_dir: Path,
    adapters_dir: Path,
    checkpoints_dir: Path,
    logs_dir: Path,
) -> StorageReport:
    return StorageReport(
        base_model_cache_bytes=directory_size(model_cache),
        dataset_bytes=directory_size(dataset_dir),
        adapters_bytes=directory_size(adapters_dir),
        checkpoints_bytes=directory_size(checkpoints_dir),
        logs_bytes=directory_size(logs_dir),
    )


def estimate_disk_usage(
    model_size_bytes: int,
    dataset_size_bytes: int,
    multiplier: float,
) -> DiskEstimate:
    adapter_bytes = max(model_size_bytes // 50, 200 * 1024 * 1024)
    checkpoint_bytes = adapter_bytes * 2
    temporary_bytes = max(dataset_size_bytes // 10, 128 * 1024 * 1024)
    return DiskEstimate(
        base_model_bytes=model_size_bytes,
        dataset_bytes=dataset_size_bytes,
        adapter_bytes=adapter_bytes,
        checkpoint_bytes=checkpoint_bytes,
        temporary_bytes=temporary_bytes,
        multiplier=multiplier,
    )


def check_disk_space(path: Path, estimate: DiskEstimate) -> DiskGuardResult:
    usage = shutil.disk_usage(path)
    result = DiskGuardResult(
        available_bytes=usage.free,
        required_bytes=estimate.required_bytes,
    )
    if not result.safe_to_start:
        raise DiskSpaceError(
            available_bytes=result.available_bytes,
            required_bytes=result.required_bytes,
        )
    return result


def guard_merged_export(path: Path, estimated_bytes: int) -> None:
    available = shutil.disk_usage(path).free
    if available < estimated_bytes:
        raise MergeExportError(
            required_bytes=estimated_bytes,
            available_bytes=available,
        )


def format_bytes(size: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        if value < BYTES_PER_UNIT:
            return f"{value:.1f} {unit}"
        value /= BYTES_PER_UNIT
    return f"{value:.1f} PB"
