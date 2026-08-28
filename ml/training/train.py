import argparse
import json
import os
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal

from ml.datasets.audit import _read_examples
from ml.hardware.report import detect_hardware
from ml.inference.chat import training_messages_for_example
from ml.evaluation.sampling import stratified_sample
from ml.training.config import ExperimentTrainingConfig, TrainingConfig, adapt_to_hardware, default_training_config, load_training_config
from ml.training.real_runtime import adapter_stats, load_tokenizer_and_lora_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("SOVYN_BASE_MODEL", ""))
    parser.add_argument("--dataset", default="ml/datasets/sovyn-v1/train.jsonl")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--method", choices=("lora", "qlora"), default="qlora")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--resume-from-checkpoint", type=Path)
    parser.add_argument("--micro", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def write_training_report(config: TrainingConfig, dry_run: bool) -> Path:
    report_path = config.output_dir / "training_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "base_model": config.model,
        "dataset_version": "sovyn-v1",
        "dataset": str(config.dataset),
        "examples": _count_jsonl(config.dataset),
        "epochs": config.epochs,
        "method": config.method,
        "adapter_parameters": None,
        "trainable_parameter_percentage": None,
        "train_loss": None,
        "validation_loss": None,
        "runtime_seconds": None,
        "gpu": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "dry_run": dry_run,
        "created_at": datetime.now(UTC).isoformat(),
        "config": _config_payload(config),
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return report_path


def main() -> int:
    args = parse_args()
    if args.config is not None:
        return _run_experiment_config(args.config, args.dry_run, args.resume_from_checkpoint, args.micro, args.output_dir)
    method: Literal["lora", "qlora"] = args.method
    config = default_training_config(
        model=args.model or "configurable-base-model",
        dataset=Path(args.dataset),
        method=method,
    )
    output_dir = args.output_dir or Path("outputs/sovyn-v1-adapter")
    config = replace(default_training_config(config.model, config.dataset, config.method), output_dir=output_dir)
    print("SOVYN Signal training")
    print(f"Model: {config.model}")
    print(f"Dataset: {config.dataset}")
    print(f"Method: {config.method}")
    print(f"Output: {config.output_dir}")
    print(f"Checkpoint limit: {config.checkpoint_limit}")
    if args.dry_run:
        report_path = write_training_report(config, dry_run=True)
        print("Dry run: no model weights loaded")
        print(f"Training report: {report_path}")
        return 0
    print("Install optional training dependencies before running full fine-tuning")
    return 2


def _run_experiment_config(
    config_path: Path,
    dry_run: bool,
    resume_from_checkpoint: Path | None,
    micro: bool,
    output_dir: Path | None,
) -> int:
    hardware = detect_hardware()
    config = adapt_to_hardware(load_training_config(config_path), hardware)
    if output_dir is not None:
        config = replace(config, output_dir=output_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = config.output_dir / ("micro_training_report.json" if micro else "training_report.json")
    payload = _experiment_report(config, hardware.cuda_available, dry_run, resume_from_checkpoint, micro)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("SOVYN EXP001 training")
    print(f"Config: {config_path}")
    print(f"Dataset: {config.dataset}")
    print(f"Output: {config.output_dir}")
    print(f"CUDA: {hardware.cuda_available}")
    print(f"Report: {report_path}")
    if dry_run:
        print("Dry run: no model weights loaded")
        return 0
    if not hardware.cuda_available:
        print("Training blocked: CUDA is unavailable")
        return 2
    if micro:
        report = _run_micro_training(config)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    print("Full training is intentionally blocked until an explicit full-training instruction is given.")
    return 2


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def _config_payload(config: TrainingConfig) -> dict[str, str | int | float | tuple[str, ...]]:
    payload = asdict(config)
    payload["dataset"] = str(config.dataset)
    payload["output_dir"] = str(config.output_dir)
    return payload


def _experiment_report(
    config: ExperimentTrainingConfig,
    cuda_available: bool,
    dry_run: bool,
    resume_from_checkpoint: Path | None,
    micro: bool,
) -> dict[str, str | int | float | bool | tuple[str, ...] | None]:
    return {
        "base_model": str(config.model_config),
        "dataset_version": "sovyn-v1",
        "dataset": str(config.dataset),
        "epochs": config.epochs,
        "method": config.method,
        "quantization": config.quantization,
        "compute_dtype": config.compute_dtype,
        "target_modules": config.target_modules,
        "gradient_accumulation": config.gradient_accumulation,
        "checkpoint_limit": config.checkpoint_limit,
        "resume_from_checkpoint": str(resume_from_checkpoint) if resume_from_checkpoint is not None else None,
        "micro": micro,
        "cuda_available": cuda_available,
        "dry_run": dry_run,
        "train_loss": None,
        "validation_loss": None,
        "adapter_parameters": None,
        "trainable_parameter_percentage": None,
        "created_at": datetime.now(UTC).isoformat(),
    }


def _run_micro_training(config: ExperimentTrainingConfig) -> dict[str, str | int | float | bool | tuple[str, ...] | None]:
    torch = _load_torch()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    for max_length in _sequence_lengths(config.max_sequence_length):
        candidate = replace(config, max_sequence_length=max_length)
        try:
            return _train_once(candidate, torch)
        except RuntimeError as error:
            if "out of memory" not in str(error).lower():
                raise
            torch.cuda.empty_cache()
            if max_length == 1024:
                raise
    raise RuntimeError("Micro training did not run")


def _train_once(config: ExperimentTrainingConfig, torch) -> dict[str, str | int | float | bool | tuple[str, ...] | None]:
    tokenizer, model, stats = load_tokenizer_and_lora_model(config)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model.config.use_cache = False
    train_batch = _tokenized_split(tokenizer, config.dataset / "train.jsonl", 256, 42, config.max_sequence_length)
    validation_batch = _tokenized_split(tokenizer, config.dataset / "validation.jsonl", 64, 43, config.max_sequence_length)
    optimizer = _optimizer(model, config.learning_rate, config.weight_decay)
    started = perf_counter()
    model.train()
    train_loss_start: float | None = None
    train_loss_end: float | None = None
    step_index = 0
    optimizer.zero_grad(set_to_none=True)
    for batch in _batches(train_batch, config.per_device_train_batch_size):
        moved = {name: value.to(model.device) for name, value in batch.items()}
        result = model(**moved)
        loss = result.loss
        observed_loss = float(loss.detach().cpu())
        if train_loss_start is None:
            train_loss_start = observed_loss
        train_loss_end = observed_loss
        (loss / config.gradient_accumulation).backward()
        step_index += 1
        if step_index % config.gradient_accumulation == 0:
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
    if step_index % config.gradient_accumulation != 0:
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
    validation_loss = _validation_loss(model, validation_batch, torch, config.per_device_train_batch_size)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)
    duration = perf_counter() - started
    return {
        **_experiment_report(config, True, False, None, True),
        "train_loss": train_loss_end,
        "training_loss_start": train_loss_start,
        "training_loss_end": train_loss_end,
        "validation_loss": validation_loss,
        "runtime_seconds": round(duration, 3),
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 4),
        "adapter_parameters": stats.trainable_parameters,
        "trainable_parameter_percentage": stats.trainable_percentage,
        "adapter_file_size_mb": _directory_size_mb(config.output_dir),
        "train_examples": 256,
        "validation_examples": 64,
        "max_sequence_length": config.max_sequence_length,
        "output_dir": str(config.output_dir),
    }


def _tokenized_split(tokenizer, path: Path, sample: int, seed: int, max_length: int):
    texts: list[str] = []
    for example in stratified_sample(_read_examples(path), sample, seed):
        messages = tuple({"role": message.role, "content": message.content} for message in training_messages_for_example(example))
        texts.append(tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False))
    tokenized = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
    tokenized["labels"] = tokenized["input_ids"].clone()
    return tokenized


def _batches(tokenized, batch_size: int):
    total = tokenized["input_ids"].shape[0]
    for start in range(0, total, batch_size):
        end = start + batch_size
        yield {name: value[start:end] for name, value in tokenized.items()}


def _validation_loss(model, tokenized, torch, batch_size: int) -> float:
    model.eval()
    losses: list[float] = []
    with torch.no_grad():
        for batch in _batches(tokenized, batch_size):
            moved = {name: value.to(model.device) for name, value in batch.items()}
            losses.append(float(model(**moved).loss.detach().cpu()))
    model.train()
    return sum(losses) / len(losses)


def _optimizer(model, learning_rate: float, weight_decay: float):
    import bitsandbytes as bnb

    return bnb.optim.PagedAdamW8bit(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=learning_rate,
        weight_decay=weight_decay,
    )


def _sequence_lengths(max_length: int) -> tuple[int, ...]:
    return tuple(dict.fromkeys(length for length in (max_length, 1536, 1024) if length <= max_length))


def _directory_size_mb(path: Path) -> float:
    size = sum(file.stat().st_size for file in path.rglob("*") if file.is_file())
    return round(size / 1024**2, 3)


def _load_torch():
    import torch

    return torch


if __name__ == "__main__":
    raise SystemExit(main())
