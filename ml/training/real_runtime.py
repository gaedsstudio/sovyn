import json
from dataclasses import dataclass
from pathlib import Path

from ml.datasets.audit import _read_examples
from ml.evaluation.sampling import stratified_sample
from ml.inference.chat import training_messages_for_example
from ml.models.config import load_model_config
from ml.training.config import ExperimentTrainingConfig


@dataclass(frozen=True, slots=True)
class AdapterStats:
    total_parameters: int
    trainable_parameters: int
    trainable_percentage: float


def load_tokenizer_and_lora_model(config: ExperimentTrainingConfig):
    transformers = _load_transformers()
    peft = _load_peft()
    torch = _load_torch()
    model_config = load_model_config(config.model_config)
    tokenizer = transformers.AutoTokenizer.from_pretrained(model_config.model_id, trust_remote_code=model_config.trust_remote_code)
    quantization = transformers.BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=_dtype(torch, config.compute_dtype))
    model = transformers.AutoModelForCausalLM.from_pretrained(
        model_config.model_id,
        trust_remote_code=model_config.trust_remote_code,
        quantization_config=quantization,
        device_map="auto",
        torch_dtype=_dtype(torch, config.compute_dtype),
    )
    model.gradient_checkpointing_enable()
    model = peft.prepare_model_for_kbit_training(model)
    lora_config = peft.LoraConfig(
        r=config.lora_rank,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=list(config.target_modules),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = peft.get_peft_model(model, lora_config)
    stats = adapter_stats(model)
    if stats.trainable_parameters == 0:
        raise RuntimeError("LoRA injection produced zero trainable parameters")
    return tokenizer, model, stats


def adapter_stats(model) -> AdapterStats:
    total = 0
    trainable = 0
    for parameter in model.parameters():
        total += parameter.numel()
        if parameter.requires_grad:
            trainable += parameter.numel()
    return AdapterStats(total, trainable, round(trainable / total * 100, 6) if total else 0.0)


def tokenized_training_sample(tokenizer, dataset: Path, max_length: int, sample: int, seed: int):
    examples = stratified_sample(_read_examples(dataset / "train.jsonl"), sample, seed)
    texts = []
    for example in examples:
        messages = tuple({"role": message.role, "content": message.content} for message in training_messages_for_example(example))
        texts.append(tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False))
    tokenized = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
    tokenized["labels"] = tokenized["input_ids"].clone()
    return tokenized


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _dtype(torch, name: str):
    if name == "bfloat16":
        return torch.bfloat16
    if name == "float16":
        return torch.float16
    return torch.float32


def _load_transformers():
    import transformers

    return transformers


def _load_peft():
    import peft

    return peft


def _load_torch():
    import torch

    return torch
