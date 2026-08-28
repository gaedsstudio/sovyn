import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ml.hardware.report import detect_hardware
from ml.models.config import load_model_config
from ml.training.config import adapt_to_hardware, load_training_config
from ml.training.real_runtime import load_tokenizer_and_lora_model, save_json, tokenized_training_sample


@dataclass(frozen=True, slots=True)
class PreflightResult:
    ok: bool
    reason: str
    cuda_available: bool
    model_id: str
    quantization: str
    dataset_exists: bool
    target_modules: tuple[str, ...]
    total_parameters: int | None
    trainable_parameters: int | None
    trainable_percentage: float | None
    idle_vram_gb: float | None
    model_loaded_vram_gb: float | None
    forward_peak_vram_gb: float | None
    backward_peak_vram_gb: float | None


def run_preflight(config_path: Path) -> PreflightResult:
    torch = _load_torch()
    config = adapt_to_hardware(load_training_config(config_path), detect_hardware())
    model = load_model_config(config.model_config)
    hardware = detect_hardware()
    dataset_exists = config.dataset.exists()
    if not hardware.cuda_available:
        return _blocked("CUDA is unavailable; QLoRA preflight requires a CUDA GPU.", model.model_id, config.quantization, dataset_exists, config.target_modules)
    if not dataset_exists:
        return _blocked("Dataset path does not exist.", model.model_id, config.quantization, False, config.target_modules)
    torch.cuda.empty_cache()
    idle = _allocated_gb(torch)
    tokenizer, lora_model, stats = load_tokenizer_and_lora_model(config)
    loaded = _allocated_gb(torch)
    batch = tokenized_training_sample(tokenizer, config.dataset, config.max_sequence_length, sample=1, seed=42)
    batch = {name: value.to(lora_model.device) for name, value in batch.items()}
    torch.cuda.reset_peak_memory_stats()
    outputs = lora_model(**batch)
    forward_peak = _peak_gb(torch)
    outputs.loss.backward()
    backward_peak = _peak_gb(torch)
    optimizer = torch.optim.AdamW((parameter for parameter in lora_model.parameters() if parameter.requires_grad), lr=config.learning_rate)
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    del optimizer, outputs, batch, lora_model, tokenizer
    torch.cuda.empty_cache()
    return PreflightResult(
        True,
        "Real Qwen3 QLoRA preflight succeeded.",
        True,
        model.model_id,
        config.quantization,
        True,
        config.target_modules,
        stats.total_parameters,
        stats.trainable_parameters,
        stats.trainable_percentage,
        idle,
        loaded,
        forward_peak,
        backward_peak,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/experiments/exp001-qwen3-4b/preflight.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_preflight(args.config)
    save_json(args.output, asdict(result))
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.ok else 2


def _blocked(reason: str, model_id: str, quantization: str, dataset_exists: bool, target_modules: tuple[str, ...]) -> PreflightResult:
    return PreflightResult(False, reason, False, model_id, quantization, dataset_exists, target_modules, None, None, None, None, None, None, None)


def _allocated_gb(torch) -> float:
    return round(torch.cuda.memory_allocated(0) / (1024**3), 4)


def _peak_gb(torch) -> float:
    return round(torch.cuda.max_memory_allocated(0) / (1024**3), 4)


def _load_torch():
    import torch

    return torch


if __name__ == "__main__":
    raise SystemExit(main())
