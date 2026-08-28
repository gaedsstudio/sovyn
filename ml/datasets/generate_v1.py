import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from ml.datasets.quality import leakage_pairs, split_examples, validate_examples
from ml.datasets.scenarios import generate_scenarios
from ml.datasets.schemas import DatasetExample, SplitName
from ml.datasets.tasks import examples_from_scenario

DEFAULT_ROOT: Final = Path("ml/datasets/sovyn-v1")
TASKS_PER_SCENARIO: Final = 8


def build_dataset(root: Path = DEFAULT_ROOT, examples: int = 20_000, seed: int = 42) -> None:
    scenario_count = max((examples + TASKS_PER_SCENARIO - 1) // TASKS_PER_SCENARIO, 1)
    scenarios = generate_scenarios(scenario_count, seed)
    raw_examples = tuple(example for scenario in scenarios for example in examples_from_scenario(scenario))[:examples]
    report = validate_examples(raw_examples)
    splits = split_examples(report.accepted)
    leaks = leakage_pairs(splits)
    if leaks:
        message = f"train/test leakage detected: {', '.join(leaks[:5])}"
        raise RuntimeError(message)
    root.mkdir(parents=True, exist_ok=True)
    for split, split_examples_ in splits.items():
        write_jsonl(root / f"{split.value}.jsonl", split_examples_)
    review_sample = sample_review_examples(splits[SplitName.CHALLENGE], report.accepted)
    write_jsonl(root / "review_sample.jsonl", review_sample)
    manifest = build_manifest(report.accepted, splits, report.duplicates, len(report.rejected))
    with (root / "manifest.json").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2, ensure_ascii=False))
        handle.write("\n")


def build_manifest(
    examples: tuple[DatasetExample, ...],
    splits: dict[SplitName, tuple[DatasetExample, ...]],
    duplicates: int,
    rejected: int,
) -> dict[str, str | int | dict[str, int]]:
    task_counts = Counter(example.task.value for example in examples)
    family_counts = Counter(example.scenario_family.value for example in examples)
    split_counts = {split.value: len(values) for split, values in splits.items()}
    return {
        "version": "sovyn-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "total_examples": len(examples),
        "tasks": dict(sorted(task_counts.items())),
        "scenario_families": dict(sorted(family_counts.items())),
        "train": split_counts[SplitName.TRAIN.value],
        "validation": split_counts[SplitName.VALIDATION.value],
        "test": split_counts[SplitName.TEST.value],
        "challenge": split_counts[SplitName.CHALLENGE.value],
        "rejected": rejected,
        "duplicates": duplicates,
    }


def sample_review_examples(challenge: tuple[DatasetExample, ...], accepted: tuple[DatasetExample, ...]) -> tuple[DatasetExample, ...]:
    prioritized = challenge + tuple(example for example in accepted if example.challenge is False)
    return prioritized[:100]


def write_jsonl(path: Path, examples: tuple[DatasetExample, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for example in examples:
            handle.write(json.dumps(_example_record(example), ensure_ascii=False))
            handle.write("\n")


def _example_record(example: DatasetExample) -> dict[str, str | bool | tuple[str, ...]]:
    record = asdict(example)
    record["task"] = example.task.value
    record["scenario_family"] = example.scenario_family.value
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=DEFAULT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_dataset(root=args.output, examples=args.examples, seed=args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
