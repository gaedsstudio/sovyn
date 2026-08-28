import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from ml.hardware.report import HardwareReport


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    model: str
    dataset: Path
    method: Literal["lora", "qlora"]
    epochs: int
    learning_rate: float
    lora_rank: int
    lora_alpha: int
    lora_dropout: float
    target_modules: tuple[str, ...]
    batch_size: int
    gradient_accumulation: int
    max_sequence_length: int
    warmup_ratio: float
    weight_decay: float
    quantization: str
    checkpoint_limit: int
    output_dir: Path


@dataclass(frozen=True, slots=True)
class ExperimentTrainingConfig:
    model_config: Path
    dataset: Path
    output_dir: Path
    method: Literal["lora", "qlora"]
    quantization: str
    compute_dtype: str
    lora_rank: int
    lora_alpha: int
    lora_dropout: float
    target_modules: tuple[str, ...]
    learning_rate: float
    epochs: int
    per_device_train_batch_size: int
    gradient_accumulation: int
    max_sequence_length: int
    warmup_ratio: float
    weight_decay: float
    gradient_checkpointing: bool
    optimizer: str
    checkpoint_limit: int
    evaluation_strategy: str


def default_training_config(model: str, dataset: Path, method: Literal["lora", "qlora"]) -> TrainingConfig:
    return TrainingConfig(
        model=model,
        dataset=dataset,
        method=method,
        epochs=1,
        learning_rate=2e-4,
        lora_rank=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=("q_proj", "k_proj", "v_proj", "o_proj"),
        batch_size=1,
        gradient_accumulation=16,
        max_sequence_length=2048,
        warmup_ratio=0.03,
        weight_decay=0.01,
        quantization="4bit",
        checkpoint_limit=2,
        output_dir=Path("outputs/sovyn-v1-adapter"),
    )


def load_training_config(path: Path) -> ExperimentTrainingConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ExperimentTrainingConfig(
        model_config=Path(raw["model_config"]),
        dataset=Path(raw["dataset"]),
        output_dir=Path(raw["output_dir"]),
        method=raw.get("method", "qlora"),
        quantization=raw.get("quantization", "4bit_nf4"),
        compute_dtype=raw.get("compute_dtype", "bfloat16"),
        lora_rank=int(raw.get("lora_rank", 16)),
        lora_alpha=int(raw.get("lora_alpha", 32)),
        lora_dropout=float(raw.get("lora_dropout", 0.05)),
        target_modules=tuple(raw.get("target_modules", ("q_proj", "k_proj", "v_proj", "o_proj"))),
        learning_rate=float(raw.get("learning_rate", 2e-4)),
        epochs=int(raw.get("epochs", 1)),
        per_device_train_batch_size=int(raw.get("per_device_train_batch_size", 1)),
        gradient_accumulation=int(raw.get("gradient_accumulation", 8)),
        max_sequence_length=int(raw.get("max_sequence_length", 2048)),
        warmup_ratio=float(raw.get("warmup_ratio", 0.03)),
        weight_decay=float(raw.get("weight_decay", 0.01)),
        gradient_checkpointing=bool(raw.get("gradient_checkpointing", True)),
        optimizer=raw.get("optimizer", "paged_adamw_8bit"),
        checkpoint_limit=int(raw.get("checkpoint_limit", 2)),
        evaluation_strategy=raw.get("evaluation_strategy", "epoch"),
    )


def adapt_to_hardware(config: ExperimentTrainingConfig, hardware: HardwareReport) -> ExperimentTrainingConfig:
    if hardware.bf16_supported is False:
        config = replace(config, compute_dtype="float16")
    if hardware.vram_total_gb is not None and hardware.vram_total_gb < 12:
        return replace(config, gradient_accumulation=max(config.gradient_accumulation, 16))
    return config
