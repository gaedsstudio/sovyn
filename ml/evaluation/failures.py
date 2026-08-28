import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from ml.datasets.schemas import DatasetExample, TaskName
from ml.evaluation.metrics import is_valid_json_output


@dataclass(frozen=True, slots=True)
class FailureRecord:
    example_id: str
    task: str
    scenario_family: str
    categories: tuple[str, ...]
    expected: str
    output: str


def classify_failures(examples: tuple[DatasetExample, ...], outputs: tuple[str, ...]) -> tuple[FailureRecord, ...]:
    failures: list[FailureRecord] = []
    for example, output in zip(examples, outputs, strict=True):
        categories = _categories(example, output)
        if categories:
            failures.append(
                FailureRecord(
                    example_id=example.example_id,
                    task=example.task.value,
                    scenario_family=example.scenario_family.value,
                    categories=categories,
                    expected=example.output,
                    output=output,
                )
            )
    return tuple(failures)


def failure_analysis(failures: tuple[FailureRecord, ...]) -> dict[str, int | dict[str, int]]:
    category_counts = Counter(category for failure in failures for category in failure.categories)
    return {
        "total_failures": len(failures),
        "categories": dict(sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))),
    }


def write_failure_artifacts(root: Path, failures: tuple[FailureRecord, ...]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "failure_analysis.json").write_text(json.dumps(failure_analysis(failures), indent=2), encoding="utf-8")
    with (root / "failures.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for failure in failures:
            handle.write(json.dumps(asdict(failure), ensure_ascii=False))
            handle.write("\n")


def _categories(example: DatasetExample, output: str) -> tuple[str, ...]:
    categories: list[str] = []
    if any(claim.lower() in output.lower() for claim in example.forbidden_claims):
        categories.extend(("unsupported_cause", "forbidden_claim"))
    if example.task in _json_tasks() and not is_valid_json_output(output):
        categories.append("invalid_json")
    if example.task is TaskName.IMPACT_CLASSIFICATION and is_valid_json_output(output) and json.loads(output) != json.loads(example.output):
        categories.append("wrong_direction")
    if example.task is TaskName.TRANSMISSION_CHAIN and is_valid_json_output(output) and json.loads(output) != json.loads(example.output):
        categories.append("wrong_transmission_chain")
    if example.task is TaskName.UNCERTAINTY_CALIBRATION and _confidence(output) > 0.6:
        categories.append("overconfident_uncertainty")
    if len(output.split()) > 95:
        categories.append("excessive_verbosity")
    if not output.strip():
        categories.append("format_violation")
    if _missing_evidence(example, output):
        categories.append("missing_evidence")
    return tuple(dict.fromkeys(categories))


def _json_tasks() -> frozenset[TaskName]:
    return frozenset(
        {
            TaskName.IMPACT_CLASSIFICATION,
            TaskName.TRANSMISSION_CHAIN,
            TaskName.EVIDENCE_FILTERING,
            TaskName.SUPPORTED_CLAIM,
            TaskName.UNCERTAINTY_CALIBRATION,
        }
    )


def _confidence(output: str) -> float:
    if not is_valid_json_output(output):
        return 1.0
    raw = json.loads(output)
    value = raw.get("confidence", 1.0)
    if isinstance(value, int | float):
        return float(value)
    return 1.0


def _missing_evidence(example: DatasetExample, output: str) -> bool:
    if example.task in {TaskName.SUPPORTED_CLAIM, TaskName.UNCERTAINTY_CALIBRATION}:
        return False
    return not any(_metric_token(claim) in output.lower() for claim in example.allowed_claims)


def _metric_token(claim: str) -> str:
    return claim.lower().split(" printed ")[0].split(" can ")[0].strip()
