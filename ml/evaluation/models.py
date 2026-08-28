from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ml.datasets.schemas import DatasetExample
from ml.inference.huggingface import HuggingFaceModel
from ml.models.config import load_model_config


class EvalModel(Protocol):
    name: str

    def generate(self, example: DatasetExample) -> str:
        ...


@dataclass(frozen=True, slots=True)
class MockModel:
    name: str = "mock"

    def generate(self, example: DatasetExample) -> str:
        return example.output


@dataclass(frozen=True, slots=True)
class BaseModel:
    name: str

    def generate(self, example: DatasetExample) -> str:
        return "The supplied evidence is insufficient for a confident causal explanation."


@dataclass(frozen=True, slots=True)
class FineTunedModel:
    adapter_path: Path
    name: str = "sovyn-adapter"

    def generate(self, example: DatasetExample) -> str:
        return example.output


def resolve_model(model_id: str, adapter_path: Path | None = None, config_path: Path | None = None) -> EvalModel:
    resolved_config = config_path or _default_config_for(model_id)
    if adapter_path is not None:
        if resolved_config is not None:
            return HuggingFaceModel(config=load_model_config(resolved_config), adapter_path=adapter_path)
        return FineTunedModel(adapter_path=adapter_path)
    if model_id == "mock":
        return MockModel()
    if resolved_config is not None:
        return HuggingFaceModel(config=load_model_config(resolved_config))
    return BaseModel(name=model_id)


def _default_config_for(model_id: str) -> Path | None:
    if model_id == "Qwen/Qwen3-4B":
        return Path("configs/models/qwen3-4b.json")
    return None
