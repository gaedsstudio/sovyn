from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import assert_never

from ml.datasets.schemas import DatasetExample
from ml.inference.chat import messages_for_example, strip_reasoning_text
from ml.models.config import ModelConfig


@dataclass(frozen=True)
class HuggingFaceModel:
    config: ModelConfig
    adapter_path: Path | None = None

    @property
    def name(self) -> str:
        return self.config.model_id

    def generate(self, example: DatasetExample) -> str:
        prompt = _format_messages(self.tokenizer, example, self.config.thinking_enabled)
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.config.max_input_length)
        inputs = {name: value.to(self.model.device) for name, value in inputs.items()}
        generation_kwargs = {
            "max_new_tokens": self.config.max_new_tokens,
            "do_sample": self.config.temperature > 0,
            "pad_token_id": self.tokenizer.eos_token_id,
        }
        if self.config.temperature > 0:
            generation_kwargs["temperature"] = self.config.temperature
        output_ids = self.model.generate(
            **inputs,
            **generation_kwargs,
        )
        generated = output_ids[0][inputs["input_ids"].shape[-1] :]
        decoded = self.tokenizer.decode(generated, skip_special_tokens=True)
        return strip_reasoning_text(decoded)

    @cached_property
    def tokenizer(self):
        transformers = _load_transformers()
        return transformers.AutoTokenizer.from_pretrained(
            self.config.model_id,
            trust_remote_code=self.config.trust_remote_code,
        )

    @cached_property
    def model(self):
        transformers = _load_transformers()
        torch = _load_torch()
        model = transformers.AutoModelForCausalLM.from_pretrained(self.config.model_id, **_model_kwargs(self.config, torch))
        if self.adapter_path is None:
            return model
        peft = _load_peft()
        return peft.PeftModel.from_pretrained(model, self.adapter_path)


def _format_messages(tokenizer, example: DatasetExample, thinking_enabled: bool) -> str:
    messages = tuple({"role": message.role, "content": message.content} for message in messages_for_example(example))
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=thinking_enabled,
    )


def _model_kwargs(config: ModelConfig, torch) -> dict[str, str | bool]:
    kwargs: dict[str, str | bool] = {
        "trust_remote_code": config.trust_remote_code,
        "device_map": config.device_map,
    }
    if config.dtype != "auto":
        kwargs["torch_dtype"] = getattr(torch, config.dtype)
    match config.quantization:
        case "none":
            return kwargs
        case "4bit":
            transformers = _load_transformers()
            kwargs["quantization_config"] = transformers.BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4")
            return kwargs
        case "8bit":
            transformers = _load_transformers()
            kwargs["quantization_config"] = transformers.BitsAndBytesConfig(load_in_8bit=True)
            return kwargs
        case unreachable:
            assert_never(unreachable)


def _load_transformers():
    try:
        import transformers
    except ImportError as error:
        raise RuntimeError("transformers is required for real Hugging Face evaluation") from error
    return transformers


def _load_torch():
    try:
        import torch
    except ImportError as error:
        raise RuntimeError("torch is required for real Hugging Face evaluation") from error
    return torch


def _load_peft():
    try:
        import peft
    except ImportError as error:
        raise RuntimeError("peft is required for adapter loading") from error
    return peft
