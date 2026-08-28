import argparse
import json
from dataclasses import asdict
from pathlib import Path

from ml.evaluation.failures import classify_failures
from ml.evaluation.metrics import evaluate_outputs, load_dataset
from ml.evaluation.models import FineTunedModel, resolve_model


def compare_models(base_model_id: str, adapter_path: Path, dataset: Path, output: Path | None = None) -> dict[str, str | dict[str, float]]:
    examples = load_dataset(dataset)
    base = resolve_model(base_model_id)
    adapter = FineTunedModel(adapter_path=adapter_path)
    base_outputs = tuple(base.generate(example) for example in examples)
    adapter_outputs = tuple(adapter.generate(example) for example in examples)
    base_metrics = evaluate_outputs(examples, base_outputs)
    adapter_metrics = evaluate_outputs(examples, adapter_outputs)
    report = {
        "dataset": str(dataset),
        "base_model": base.name,
        "adapter": str(adapter_path),
        "base_metrics": asdict(base_metrics),
        "adapter_metrics": asdict(adapter_metrics),
        "success_gates": success_gates(asdict(base_metrics), asdict(adapter_metrics)),
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        write_report_markdown(output.parent / "REPORT.md", report)
        write_human_review(output.parent / "human_review.jsonl", examples, base_outputs, adapter_outputs)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=Path("ml/datasets/sovyn-v1/test.jsonl"))
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = compare_models(args.base, args.adapter, args.dataset, args.output)
    print("BASE MODEL")
    print(json.dumps(report["base_metrics"], indent=2))
    print("SOVYN ADAPTER")
    print(json.dumps(report["adapter_metrics"], indent=2))
    return 0


def success_gates(base: dict[str, float], adapter: dict[str, float]) -> dict[str, bool | str]:
    gates = {
        "unsupported_claim_rate": adapter["unsupported_claim_rate"] <= base["unsupported_claim_rate"],
        "forbidden_claim_rate": adapter["forbidden_claim_rate"] <= base["forbidden_claim_rate"],
        "json_validity": adapter["json_validity"] >= base["json_validity"],
        "direction_accuracy": adapter["direction_accuracy"] >= base["direction_accuracy"],
        "uncertainty_compliance": adapter["uncertainty_compliance"] >= base["uncertainty_compliance"],
    }
    verdict = "PASS" if all(gates.values()) else "MIXED"
    return {**gates, "verdict": verdict}


def write_report_markdown(path: Path, report: dict) -> None:
    base = report["base_metrics"]
    adapter = report["adapter_metrics"]
    lines = [
        "# SOVYN Signal Model - EXP001",
        "",
        "| Metric | BASE | SOVYN | DELTA |",
        "|---|---:|---:|---:|",
    ]
    for metric, base_value in base.items():
        adapter_value = adapter[metric]
        lines.append(f"| {metric} | {base_value:.4f} | {adapter_value:.4f} | {adapter_value - base_value:.4f} |")
    lines.extend(("", f"Verdict: {report['success_gates']['verdict']}"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_human_review(path: Path, examples: tuple, base_outputs: tuple[str, ...], adapter_outputs: tuple[str, ...]) -> None:
    failures = classify_failures(examples, adapter_outputs)
    flagged = {failure.example_id: failure.categories for failure in failures}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for example, base_output, adapter_output in tuple(zip(examples, base_outputs, adapter_outputs, strict=True))[:100]:
            handle.write(
                json.dumps(
                    {
                        "base_answer": base_output,
                        "sovyn_answer": adapter_output,
                        "ground_truth": example.output,
                        "evidence": example.input,
                        "task": example.task.value,
                        "scenario_family": example.scenario_family.value,
                        "automatic_flags": flagged.get(example.example_id, ()),
                    },
                    ensure_ascii=False,
                )
            )
            handle.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
