from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from sovyn_training.errors import ConfigFileError


class CacheSettings(BaseSettings):
    model_cache: Path | None = Field(default=None, alias="SOVYN_MODEL_CACHE")
    data_cache: Path | None = Field(default=None, alias="SOVYN_DATA_CACHE")
    base_model: str | None = Field(default=None, alias="SOVYN_BASE_MODEL")
    dev_model: str | None = Field(default=None, alias="SOVYN_DEV_MODEL")

    model_config = SettingsConfigDict(extra="ignore")


class ModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    load_in_4bit: bool = True
    bnb_4bit_quant_type: Literal["nf4", "fp4"] = "nf4"
    bnb_4bit_compute_dtype: Literal["bfloat16", "float16"] = "bfloat16"


class LoraConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    r: int = Field(default=16, ge=1)
    alpha: int = Field(default=32, ge=1)
    dropout: float = Field(default=0.05, ge=0.0, le=1.0)
    target_modules: tuple[str, ...] = ("q_proj", "v_proj")


class TrainingConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    epochs: int = Field(default=2, ge=1)
    batch_size: int = Field(default=1, ge=1)
    gradient_accumulation_steps: int = Field(default=16, ge=1)
    save_strategy: Literal["steps", "epoch", "no"] = "steps"
    save_total_limit: int = Field(default=2, ge=1, le=2)
    save_optimizer_state: bool = False
    resume_training: bool = False
    max_seq_length: int = Field(default=2048, ge=128)

    @field_validator("save_optimizer_state")
    @classmethod
    def optimizer_requires_resume(cls, value: bool) -> bool:
        return value


class DatasetConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    streaming: bool = True
    cache_tokenized: bool = False
    max_samples: int | None = Field(default=None, ge=1)


class StorageConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_root: Path = Path("training/outputs")
    adapter_name: str = "sovyn-qlora-v0.1"
    merge_model_after_training: bool = False
    cleanup_temp: bool = True
    required_disk_multiplier: float = Field(default=1.25, ge=1.0)


class SovynTrainingConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: ModelConfig
    lora: LoraConfig
    training: TrainingConfig
    dataset: DatasetConfig
    storage: StorageConfig

    @property
    def adapter_output_dir(self) -> Path:
        return self.storage.output_root / "adapters" / self.storage.adapter_name

    @property
    def checkpoint_dir(self) -> Path:
        return self.storage.output_root / "checkpoints"

    def with_env_overrides(self, settings: CacheSettings) -> Self:
        model_id = settings.base_model or settings.dev_model or self.model.id
        model = self.model.model_copy(update={"id": model_id})
        return self.model_copy(update={"model": model})


def load_training_config(
    path: Path,
    settings: CacheSettings | None = None,
) -> SovynTrainingConfig:
    if not path.exists():
        raise ConfigFileError(path=path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    config = SovynTrainingConfig.model_validate(raw)
    cache_settings = settings or CacheSettings()
    return config.with_env_overrides(cache_settings)
