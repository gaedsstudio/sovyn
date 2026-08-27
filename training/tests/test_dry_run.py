from pathlib import Path

from sovyn_training.config import CacheSettings, load_training_config
from sovyn_training.trainers.dry_run import run_dry_run
from test_config import write_config


def test_dry_run_when_dataset_has_duplicate_samples(tmp_path: Path) -> None:
    dataset = tmp_path / "samples.jsonl"
    dataset.write_text(
        (
            '{"messages":[{"role":"user","content":"same"}]}\n'
            '{"messages":[{"role":"user","content":"same"}]}\n'
            '{"messages":[{"role":"user","content":"other"}]}'
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "qlora.yaml"
    write_config(config_path, dataset)
    config = load_training_config(config_path, settings=CacheSettings())

    report = run_dry_run(config, CacheSettings(), tmp_path)

    assert report.sample_count == 2
    assert report.adapter_output_dir == tmp_path / "outputs" / "adapters" / "sovyn-test"
    assert report.cache_tokenized_dataset is False
    assert report.merge_model_after_training is False
