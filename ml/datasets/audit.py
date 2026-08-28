import argparse
import json
from collections import Counter
from pathlib import Path

from ml.datasets.quality import example_signature
from ml.datasets.schemas import DatasetExample, ScenarioFamily, ScenarioId, SplitName, TaskName


def audit_dataset(root: Path) -> dict[str, int | float | dict[str, int]]:
    examples = tuple(_read_examples(root / f"{split.value}.jsonl") for split in SplitName)
    flat = tuple(example for group in examples for example in group)
    duplicate_count = len(flat) - len({example_signature(example) for example in flat})
    unsupported = sum(_has_forbidden_claim(example) for example in flat)
    json_failures = sum(_json_task_failure(example) for example in flat)
    total = len(flat)
    return {
        "examples": total,
        "valid": total - unsupported - json_failures,
        "rejected": _manifest_int(root, "rejected"),
        "duplicates": duplicate_count,
        "duplicate_rate": round(duplicate_count / total, 4) if total else 0.0,
        "unsupported_claims": unsupported,
        "json_failures": json_failures,
        "tasks": dict(sorted(Counter(example.task.value for example in flat).items())),
        "scenario_coverage": dict(sorted(Counter(example.scenario_family.value for example in flat).items())),
    }


def render_audit(root: Path) -> str:
    audit = audit_dataset(root)
    lines = [
        "SOVYN Dataset Audit",
        "",
        f"Examples             {audit['examples']}",
        f"Valid                {audit['valid']}",
        f"Rejected             {audit['rejected']}",
        f"Duplicates           {audit['duplicates']} ({audit['duplicate_rate']:.2%})",
        f"Unsupported claims   {audit['unsupported_claims']}",
        f"JSON failures        {audit['json_failures']}",
        "",
        "Tasks",
    ]
    lines.extend(f"{name:<24}{count}" for name, count in audit["tasks"].items())
    lines.append("")
    lines.append("Scenario coverage")
    lines.extend(f"{name:<24}{count}" for name, count in audit["scenario_coverage"].items())
    return "\n".join(lines)


def _read_examples(path: Path) -> tuple[DatasetExample, ...]:
    if not path.exists():
        return ()
    examples: list[DatasetExample] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            examples.append(
                DatasetExample(
                    example_id=record["example_id"],
                    scenario_id=ScenarioId(record["scenario_id"]),
                    scenario_family=ScenarioFamily(record["scenario_family"]),
                    task=TaskName(record["task"]),
                    instruction=record["instruction"],
                    input=record["input"],
                    output=record["output"],
                    allowed_claims=tuple(record["allowed_claims"]),
                    forbidden_claims=tuple(record["forbidden_claims"]),
                    challenge=bool(record["challenge"]),
                )
            )
    return tuple(examples)


def _has_forbidden_claim(example: DatasetExample) -> bool:
    return any(claim.lower() in example.output.lower() for claim in example.forbidden_claims)


def _json_task_failure(example: DatasetExample) -> bool:
    if example.task not in {
        TaskName.IMPACT_CLASSIFICATION,
        TaskName.TRANSMISSION_CHAIN,
        TaskName.EVIDENCE_FILTERING,
        TaskName.SUPPORTED_CLAIM,
        TaskName.UNCERTAINTY_CALIBRATION,
    }:
        return False
    try:
        json.loads(example.output)
    except json.JSONDecodeError:
        return True
    return False


def _manifest_int(root: Path, key: str) -> int:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    value = manifest.get(key, 0)
    if isinstance(value, int):
        return value
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(render_audit(args.dataset))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
