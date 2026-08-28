import json
from dataclasses import dataclass
from pathlib import Path

from ml.datasets.audit import _read_examples
from ml.datasets.schemas import DatasetExample, TaskName


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    json_validity: float
    direction_accuracy: float
    relationship_accuracy: float
    unsupported_claim_rate: float
    forbidden_claim_rate: float
    evidence_precision: float
    evidence_recall: float
    uncertainty_compliance: float
    concise_format_compliance: float


def is_valid_json_output(value: str) -> bool:
    try:
        json.loads(value)
    except json.JSONDecodeError:
        return False
    return True


def unsupported_claim_rate(outputs: tuple[str, ...], unsupported_terms: tuple[str, ...]) -> float:
    if len(outputs) == 0:
        return 0.0
    flagged = sum(
        1
        for output in outputs
        if any(term.lower() in output.lower() for term in unsupported_terms)
    )
    return flagged / len(outputs)


def evaluate_outputs(examples: tuple[DatasetExample, ...], outputs: tuple[str, ...]) -> EvaluationMetrics:
    json_tasks = tuple(
        index
        for index, example in enumerate(examples)
        if example.task
        in {
            TaskName.IMPACT_CLASSIFICATION,
            TaskName.TRANSMISSION_CHAIN,
            TaskName.EVIDENCE_FILTERING,
            TaskName.SUPPORTED_CLAIM,
            TaskName.UNCERTAINTY_CALIBRATION,
        }
    )
    json_valid = _rate(tuple(is_valid_json_output(outputs[index]) for index in json_tasks))
    direction = _direction_accuracy(examples, outputs)
    relationship = _relationship_accuracy(examples, outputs)
    forbidden = _rate(tuple(_contains_forbidden(example, output) for example, output in zip(examples, outputs, strict=True)))
    evidence_precision = _evidence_precision(examples, outputs)
    evidence_recall = _evidence_recall(examples, outputs)
    uncertainty = _uncertainty_compliance(examples, outputs)
    concise = _rate(tuple(len(output.split()) <= 95 for output in outputs))
    return EvaluationMetrics(
        json_validity=json_valid,
        direction_accuracy=direction,
        relationship_accuracy=relationship,
        unsupported_claim_rate=forbidden,
        forbidden_claim_rate=forbidden,
        evidence_precision=evidence_precision,
        evidence_recall=evidence_recall,
        uncertainty_compliance=uncertainty,
        concise_format_compliance=concise,
    )


@dataclass(frozen=True, slots=True)
class TaskMetric:
    task: str
    count: int
    json_validity: float | None
    forbidden_claim_rate: float
    concise_format_compliance: float


def load_dataset(path: Path) -> tuple[DatasetExample, ...]:
    return _read_examples(path)


def task_metrics(examples: tuple[DatasetExample, ...], outputs: tuple[str, ...]) -> tuple[TaskMetric, ...]:
    metrics: list[TaskMetric] = []
    for task in TaskName:
        pairs = tuple((example, output) for example, output in zip(examples, outputs, strict=True) if example.task is task)
        if not pairs:
            continue
        task_examples = tuple(pair[0] for pair in pairs)
        task_outputs = tuple(pair[1] for pair in pairs)
        json_values = tuple(is_valid_json_output(output) for output in task_outputs if task in _json_tasks())
        metrics.append(
            TaskMetric(
                task=task.value,
                count=len(pairs),
                json_validity=_rate(json_values) if json_values else None,
                forbidden_claim_rate=_rate(tuple(_contains_forbidden(example, output) for example, output in pairs)),
                concise_format_compliance=_rate(tuple(len(output.split()) <= 95 for output in task_outputs)),
            )
        )
    return tuple(metrics)


def _direction_accuracy(examples: tuple[DatasetExample, ...], outputs: tuple[str, ...]) -> float:
    checks: list[bool] = []
    for example, output in zip(examples, outputs, strict=True):
        if example.task is not TaskName.IMPACT_CLASSIFICATION:
            continue
        expected = json.loads(example.output)
        actual = json.loads(output) if is_valid_json_output(output) else {}
        checks.append(expected == actual)
    return _rate(tuple(checks))


def _relationship_accuracy(examples: tuple[DatasetExample, ...], outputs: tuple[str, ...]) -> float:
    checks: list[bool] = []
    for example, output in zip(examples, outputs, strict=True):
        if example.task is not TaskName.TRANSMISSION_CHAIN:
            continue
        expected = json.loads(example.output)
        actual = json.loads(output) if is_valid_json_output(output) else []
        checks.append(expected == actual)
    return _rate(tuple(checks))


def _evidence_precision(examples: tuple[DatasetExample, ...], outputs: tuple[str, ...]) -> float:
    checks = tuple(not _contains_forbidden(example, output) for example, output in zip(examples, outputs, strict=True))
    return _rate(checks)


def _evidence_recall(examples: tuple[DatasetExample, ...], outputs: tuple[str, ...]) -> float:
    checks: list[bool] = []
    for example, output in zip(examples, outputs, strict=True):
        allowed_tokens = tuple(_evidence_tokens(example))
        checks.append(any(token and token in output.lower() for token in allowed_tokens))
    return _rate(tuple(checks))


def _uncertainty_compliance(examples: tuple[DatasetExample, ...], outputs: tuple[str, ...]) -> float:
    checks: list[bool] = []
    for example, output in zip(examples, outputs, strict=True):
        if example.task is TaskName.UNCERTAINTY_CALIBRATION:
            checks.append(is_valid_json_output(output) and json.loads(output).get("confidence", 1) <= 0.6)
    return _rate(tuple(checks))


def _contains_forbidden(example: DatasetExample, output: str) -> bool:
    return any(claim.lower() in output.lower() for claim in example.forbidden_claims)


def _claim_token(claim: str) -> str:
    return claim.lower().split(" can ")[0].split(" printed ")[0].strip()


def _evidence_tokens(example: DatasetExample) -> tuple[str, ...]:
    raw = " ".join((example.input, " ".join(example.allowed_claims))).lower()
    tokens = tuple(
        token
        for token in _structured_tokens(raw)
        if token not in {"task", "input", "facts", "output"}
    )
    if tokens:
        return tokens
    return tuple(_claim_token(claim) for claim in example.allowed_claims)


def _structured_tokens(raw: str) -> tuple[str, ...]:
    candidates = []
    for separator in ('"', "'", " ", ",", "{", "}", "[", "]", ":"):
        raw = raw.replace(separator, "\n")
    for line in raw.splitlines():
        value = line.strip().lower()
        if "_" in value or "/" in value:
            candidates.append(value)
    return tuple(dict.fromkeys(candidates))


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


def _rate(values: tuple[bool, ...]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
