import argparse
import json
from dataclasses import asdict
from pathlib import Path

from ml.datasets.schemas import DatasetExample
from ml.evaluation.failures import classify_failures, write_failure_artifacts
from ml.evaluation.metrics import evaluate_outputs, load_dataset, task_metrics
from ml.evaluation.models import resolve_model
from ml.evaluation.sampling import stratified_sample


def run_benchmark(
    model_id: str,
    dataset: Path,
    output: Path | None = None,
    sample: int | None = None,
    seed: int = 42,
    config: Path | None = None,
    predictions: Path | None = None,
    sample_ids_output: Path | None = None,
    sample_ids_input: Path | None = None,
    adapter_path: Path | None = None,
) -> dict[str, str | int | dict[str, float] | list[dict[str, str | int | float | None]]]:
    examples = _select_examples(load_dataset(dataset), sample, seed, sample_ids_input)
    model = resolve_model(model_id, adapter_path=adapter_path, config_path=config)
    outputs = _generate_outputs(model, examples, predictions)
    metrics = evaluate_outputs(examples, outputs)
    failures = classify_failures(examples, outputs)
    report = {
        "model": model.name,
        "dataset": str(dataset),
        "sample_size": len(examples),
        "metrics": asdict(metrics),
        "task_metrics": [asdict(metric) for metric in task_metrics(examples, outputs)],
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        write_failure_artifacts(output.parent, failures)
        _write_config(output.parent / "config.json", model_id, dataset, sample, seed, config)
    if sample_ids_output is not None:
        _write_sample_ids(sample_ids_output, examples)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="mock")
    parser.add_argument("--dataset", type=Path, default=Path("ml/datasets/sovyn-v1/test.jsonl"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--sample", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--sample-ids-output", type=Path)
    parser.add_argument("--sample-ids-input", type=Path)
    parser.add_argument("--adapter-path", type=Path)
    parser.add_argument("--load-in-4bit", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_benchmark(
        args.model,
        args.dataset,
        args.output,
        args.sample,
        args.seed,
        args.config,
        args.predictions,
        args.sample_ids_output,
        args.sample_ids_input,
        args.adapter_path,
    )
    print(json.dumps(report, indent=2))
    return 0


def _select_examples(
    examples: tuple[DatasetExample, ...],
    sample: int | None,
    seed: int,
    sample_ids_input: Path | None,
) -> tuple[DatasetExample, ...]:
    if sample_ids_input is None:
        return stratified_sample(examples, sample, seed)
    sample_ids = json.loads(sample_ids_input.read_text(encoding="utf-8"))
    by_id = {example.example_id: example for example in examples}
    return tuple(by_id[example_id] for example_id in sample_ids)


def _write_predictions(path: Path, examples: tuple[DatasetExample, ...], outputs: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for example, output in zip(examples, outputs, strict=True):
            handle.write(
                json.dumps(
                    {
                        "example_id": example.example_id,
                        "task": example.task.value,
                        "scenario_family": example.scenario_family.value,
                        "expected": example.output,
                        "prediction": output,
                    },
                    ensure_ascii=False,
                )
            )
            handle.write("\n")


def _generate_outputs(model, examples: tuple[DatasetExample, ...], predictions: Path | None) -> tuple[str, ...]:
    outputs: list[str] = []
    if predictions is not None:
        predictions.parent.mkdir(parents=True, exist_ok=True)
    handle = predictions.open("w", encoding="utf-8", newline="\n") if predictions is not None else None
    try:
        for index, example in enumerate(examples, start=1):
            output = model.generate(example)
            outputs.append(output)
            if handle is not None:
                _write_prediction(handle, example, output)
            if index == 1 or index % 10 == 0 or index == len(examples):
                print(f"generated {index}/{len(examples)}", flush=True)
    finally:
        if handle is not None:
            handle.close()
    return tuple(outputs)


def _write_prediction(handle, example: DatasetExample, output: str) -> None:
    handle.write(
        json.dumps(
            {
                "example_id": example.example_id,
                "task": example.task.value,
                "scenario_family": example.scenario_family.value,
                "expected": example.output,
                "prediction": output,
            },
            ensure_ascii=False,
        )
    )
    handle.write("\n")
    handle.flush()


def _write_sample_ids(path: Path, examples: tuple[DatasetExample, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([example.example_id for example in examples], indent=2), encoding="utf-8")


def _write_config(path: Path, model_id: str, dataset: Path, sample: int | None, seed: int, config: Path | None) -> None:
    payload = {
        "model": model_id,
        "dataset": str(dataset),
        "sample": sample,
        "seed": seed,
        "config": str(config) if config is not None else None,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
