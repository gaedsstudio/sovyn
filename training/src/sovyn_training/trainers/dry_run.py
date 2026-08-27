from dataclasses import dataclass
from pathlib import Path

from sovyn_training.config import CacheSettings, SovynTrainingConfig
from sovyn_training.datasets.dedup import deduplicate_samples
from sovyn_training.datasets.streaming import stream_jsonl
from sovyn_training.models.paths import resolve_training_paths
from sovyn_training.tools.storage import (
    DiskGuardResult,
    StorageReport,
    build_storage_report,
    check_disk_space,
    directory_size,
    estimate_disk_usage,
)

DEFAULT_DEV_MODEL_BYTES = 1_200_000_000


@dataclass(frozen=True, slots=True)
class DryRunReport:
    model_id: str
    dataset_source: str
    sample_count: int
    adapter_output_dir: Path
    disk_guard: DiskGuardResult
    storage_report: StorageReport
    cache_tokenized_dataset: bool
    merge_model_after_training: bool


def count_streamed_samples(config: SovynTrainingConfig) -> int:
    dataset_path = Path(config.dataset.source)
    if not dataset_path.exists():
        return 0
    samples = stream_jsonl(dataset_path, max_samples=config.dataset.max_samples)
    return sum(1 for _sample in deduplicate_samples(samples))


def run_dry_run(
    config: SovynTrainingConfig,
    settings: CacheSettings,
    workspace_root: Path,
) -> DryRunReport:
    paths = resolve_training_paths(config, settings)
    dataset_path = Path(config.dataset.source)
    model_bytes = directory_size(paths.model_cache) or DEFAULT_DEV_MODEL_BYTES
    dataset_bytes = directory_size(dataset_path)
    estimate = estimate_disk_usage(
        model_size_bytes=model_bytes,
        dataset_size_bytes=dataset_bytes,
        multiplier=config.storage.required_disk_multiplier,
    )
    disk_guard = check_disk_space(workspace_root, estimate)
    report = build_storage_report(
        model_cache=paths.model_cache,
        dataset_dir=dataset_path.parent,
        adapters_dir=paths.adapter_dir.parent,
        checkpoints_dir=paths.checkpoint_dir,
        logs_dir=paths.logs_dir,
    )
    return DryRunReport(
        model_id=config.model.id,
        dataset_source=config.dataset.source,
        sample_count=count_streamed_samples(config),
        adapter_output_dir=paths.adapter_dir,
        disk_guard=disk_guard,
        storage_report=report,
        cache_tokenized_dataset=config.dataset.cache_tokenized,
        merge_model_after_training=config.storage.merge_model_after_training,
    )
