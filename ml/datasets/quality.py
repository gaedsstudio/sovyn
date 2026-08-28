import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Final

from ml.datasets.schemas import DatasetExample, SplitName, TaskName
from ml.datasets.tasks import JSON_TASKS

MAX_SEQUENCE_CHARS: Final = 6500
TOKEN_RE: Final = re.compile(r"[a-z0-9_/.-]+")


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    example_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    accepted: tuple[DatasetExample, ...]
    rejected: tuple[ValidationIssue, ...]
    duplicates: int
    leakage_pairs: tuple[str, ...]


def validate_examples(examples: tuple[DatasetExample, ...]) -> ValidationReport:
    rejected: list[ValidationIssue] = []
    prelim: list[DatasetExample] = []
    for example in examples:
        reason = _invalid_reason(example)
        if reason is None:
            prelim.append(example)
        else:
            rejected.append(ValidationIssue(example.example_id, reason))
    accepted, duplicates = deduplicate(tuple(prelim))
    return ValidationReport(accepted=accepted, rejected=tuple(rejected), duplicates=duplicates, leakage_pairs=())


def deduplicate(examples: tuple[DatasetExample, ...]) -> tuple[tuple[DatasetExample, ...], int]:
    kept: list[DatasetExample] = []
    seen: set[str] = set()
    duplicate_count = 0
    for example in examples:
        signature = example_signature(example)
        if signature in seen or _near_duplicate(example, tuple(kept[-80:])):
            duplicate_count += 1
            continue
        seen.add(signature)
        kept.append(example)
    return tuple(kept), duplicate_count


def example_signature(example: DatasetExample) -> str:
    normalized = _normalize(f"{example.scenario_family.value}|{example.task.value}|{example.input}|{example.output}")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def split_examples(examples: tuple[DatasetExample, ...]) -> dict[SplitName, tuple[DatasetExample, ...]]:
    buckets: dict[SplitName, list[DatasetExample]] = {split: [] for split in SplitName}
    for example in examples:
        if example.challenge:
            buckets[SplitName.CHALLENGE].append(example)
            continue
        selector = int(hashlib.sha256(example.scenario_id.encode("utf-8")).hexdigest()[:8], 16) % 10
        if selector == 0:
            buckets[SplitName.TEST].append(example)
        elif selector == 1:
            buckets[SplitName.VALIDATION].append(example)
        else:
            buckets[SplitName.TRAIN].append(example)
    _rebalance_empty_splits(buckets)
    return {split: tuple(values) for split, values in buckets.items()}


def leakage_pairs(splits: dict[SplitName, tuple[DatasetExample, ...]]) -> tuple[str, ...]:
    ownership: dict[str, SplitName] = {}
    leaks: list[str] = []
    for split, examples in splits.items():
        if split is SplitName.CHALLENGE:
            continue
        for example in examples:
            previous = ownership.get(example.scenario_id)
            if previous is not None and previous is not split:
                leaks.append(f"{example.scenario_id}:{previous.value}->{split.value}")
            ownership[example.scenario_id] = split
    return tuple(leaks)


def _invalid_reason(example: DatasetExample) -> str | None:
    if not example.example_id or not example.instruction or not example.input or not example.output:
        return "required field missing"
    if len(example.instruction) + len(example.input) + len(example.output) > MAX_SEQUENCE_CHARS:
        return "sequence too long"
    if _contains_nan(example.input) or _contains_nan(example.output):
        return "NaN value"
    if any(claim.lower() in example.output.lower() for claim in example.forbidden_claims):
        return "forbidden claim"
    if any(phrase in example.output.lower() for phrase in ("game-changing", "massive opportunity", "investors panicked")):
        return "style violation"
    if example.task in JSON_TASKS and not _json_loads(example.output):
        return "JSON output failure"
    return None


def _contains_nan(value: str) -> bool:
    return re.search(r"\bnan\b", value, flags=re.IGNORECASE) is not None or any(math.isnan(number) for number in _numbers(value))


def _numbers(value: str) -> tuple[float, ...]:
    found: list[float] = []
    for token in re.findall(r"-?\d+(?:\.\d+)?", value):
        found.append(float(token))
    return tuple(found)


def _json_loads(value: str) -> bool:
    try:
        json.loads(value)
    except json.JSONDecodeError:
        return False
    return True


def _near_duplicate(example: DatasetExample, candidates: tuple[DatasetExample, ...]) -> bool:
    tokens = set(TOKEN_RE.findall(_normalize(example.input)))
    if not tokens:
        return False
    for candidate in candidates:
        candidate_tokens = set(TOKEN_RE.findall(_normalize(candidate.input)))
        overlap = len(tokens & candidate_tokens) / len(tokens | candidate_tokens)
        if example.task is candidate.task and overlap > 0.92:
            return True
    return False


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def _rebalance_empty_splits(buckets: dict[SplitName, list[DatasetExample]]) -> None:
    for split in (SplitName.TRAIN, SplitName.VALIDATION, SplitName.TEST):
        if buckets[split]:
            continue
        donor = max((SplitName.TRAIN, SplitName.VALIDATION, SplitName.TEST), key=lambda item: len(buckets[item]))
        if buckets[donor]:
            scenario_id = buckets[donor][-1].scenario_id
            moved = tuple(example for example in buckets[donor] if example.scenario_id == scenario_id)
            buckets[donor][:] = [example for example in buckets[donor] if example.scenario_id != scenario_id]
            buckets[split].extend(moved)
