from pathlib import Path

import typer

from sovyn_training.config import CacheSettings, load_training_config
from sovyn_training.tools.storage import build_storage_report, format_bytes


def main() -> None:
    settings = CacheSettings()
    config = load_training_config(Path("configs/qlora_dev.yaml"), settings=settings)
    output_root = config.storage.output_root
    report = build_storage_report(
        model_cache=settings.model_cache,
        dataset_dir=Path(config.dataset.source).parent,
        adapters_dir=output_root / "adapters",
        checkpoints_dir=output_root / "checkpoints",
        logs_dir=output_root / "logs",
    )
    typer.echo(f"Base model cache     {format_bytes(report.base_model_cache_bytes)}")
    typer.echo(f"Dataset              {format_bytes(report.dataset_bytes)}")
    typer.echo(f"LoRA adapter         {format_bytes(report.adapters_bytes)}")
    typer.echo(f"Checkpoints          {format_bytes(report.checkpoints_bytes)}")
    typer.echo(f"Total SOVYN files    {format_bytes(report.sovyn_bytes)}")


if __name__ == "__main__":
    main()
