from pathlib import Path

from sovyn_training.config import CacheSettings, load_training_config


def write_config(path: Path, dataset: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "model:",
                '  id: "base/model"',
                "lora:",
                "  r: 8",
                "  alpha: 16",
                "training:",
                "  save_total_limit: 2",
                "  save_optimizer_state: false",
                "  resume_training: false",
                "dataset:",
                f'  source: "{dataset.as_posix()}"',
                "  streaming: true",
                "  cache_tokenized: false",
                "storage:",
                f'  output_root: "{path.parent.as_posix()}/outputs"',
                '  adapter_name: "sovyn-test"',
                "  merge_model_after_training: false",
            ],
        ),
        encoding="utf-8",
    )


def test_config_loading_when_env_dev_model_is_set(tmp_path: Path) -> None:
    dataset = tmp_path / "samples.jsonl"
    config_path = tmp_path / "qlora.yaml"
    write_config(config_path, dataset)
    settings = CacheSettings(SOVYN_DEV_MODEL="dev/model")

    config = load_training_config(config_path, settings=settings)

    assert config.model.id == "dev/model"
    assert config.dataset.streaming is True
    assert config.dataset.cache_tokenized is False
    assert config.adapter_output_dir == tmp_path / "outputs" / "adapters" / "sovyn-test"
