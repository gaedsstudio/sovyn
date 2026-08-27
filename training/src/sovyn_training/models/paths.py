from dataclasses import dataclass
from pathlib import Path

from sovyn_training.config import CacheSettings, SovynTrainingConfig


@dataclass(frozen=True, slots=True)
class TrainingPaths:
    adapter_dir: Path
    checkpoint_dir: Path
    logs_dir: Path
    model_cache: Path | None
    data_cache: Path | None


def resolve_training_paths(
    config: SovynTrainingConfig,
    settings: CacheSettings,
) -> TrainingPaths:
    output_root = config.storage.output_root
    return TrainingPaths(
        adapter_dir=config.adapter_output_dir,
        checkpoint_dir=config.checkpoint_dir,
        logs_dir=output_root / "logs",
        model_cache=settings.model_cache,
        data_cache=settings.data_cache,
    )
