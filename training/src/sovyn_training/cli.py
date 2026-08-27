from pathlib import Path

import typer

from sovyn_training.config import CacheSettings, load_training_config
from sovyn_training.tools.checkpoints import (
    cleanup_checkpoints,
    cleanup_temporary_files,
)
from sovyn_training.tools.storage import build_storage_report, format_bytes
from sovyn_training.trainers.dry_run import run_dry_run

app = typer.Typer(no_args_is_help=True)


@app.command()
def train(
    config: Path = typer.Option(Path("configs/qlora_dev.yaml"), "--config"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    max_samples: int | None = typer.Option(None, "--max-samples", "--sample"),
) -> None:
    settings = CacheSettings()
    training_config = load_training_config(config, settings=settings)
    if max_samples is not None:
        dataset = training_config.dataset.model_copy(
            update={"max_samples": max_samples},
        )
        training_config = training_config.model_copy(update={"dataset": dataset})
    if dry_run:
        report = run_dry_run(training_config, settings, Path.cwd())
        typer.echo("SOVYN training dry run")
        typer.echo(f"Model: {report.model_id}")
        typer.echo(f"Dataset: {report.dataset_source}")
        typer.echo(f"Samples inspected: {report.sample_count}")
        typer.echo(f"Adapter output: {report.adapter_output_dir}")
        typer.echo(f"Available disk: {format_bytes(report.disk_guard.available_bytes)}")
        typer.echo(
            f"Estimated required: {format_bytes(report.disk_guard.required_bytes)}",
        )
        typer.echo("Safe to start: YES")
        return
    typer.echo(
        "Install optional qlora dependencies and run with an approved GPU profile.",
    )
    raise typer.Exit(code=2)


@app.command()
def storage(
    config: Path = typer.Option(Path("configs/qlora_dev.yaml"), "--config"),
) -> None:
    settings = CacheSettings()
    training_config = load_training_config(config, settings=settings)
    output_root = training_config.storage.output_root
    report = build_storage_report(
        model_cache=settings.model_cache,
        dataset_dir=Path(training_config.dataset.source).parent,
        adapters_dir=output_root / "adapters",
        checkpoints_dir=output_root / "checkpoints",
        logs_dir=output_root / "logs",
    )
    typer.echo("SOVYN Storage")
    typer.echo(f"Base model cache     {format_bytes(report.base_model_cache_bytes)}")
    typer.echo(f"Dataset              {format_bytes(report.dataset_bytes)}")
    typer.echo(f"Adapters             {format_bytes(report.adapters_bytes)}")
    typer.echo(f"Checkpoints          {format_bytes(report.checkpoints_bytes)}")
    typer.echo(f"Logs                 {format_bytes(report.logs_bytes)}")
    typer.echo(f"Total SOVYN files    {format_bytes(report.sovyn_bytes)}")
    typer.echo(f"Total incl. cache    {format_bytes(report.total_bytes)}")


@app.command()
def clean(
    config: Path = typer.Option(Path("configs/qlora_dev.yaml"), "--config"),
    deep: bool = typer.Option(False, "--deep"),
) -> None:
    training_config = load_training_config(config, settings=CacheSettings())
    output_root = training_config.storage.output_root
    removed = [
        *cleanup_checkpoints(output_root / "checkpoints", keep=2),
        *cleanup_temporary_files(output_root),
    ]
    typer.echo(f"Removed {len(removed)} generated training artifact(s).")
    if deep:
        typer.echo(
            "Deep clean intentionally leaves shared Hugging Face cache untouched.",
        )


if __name__ == "__main__":
    app()
