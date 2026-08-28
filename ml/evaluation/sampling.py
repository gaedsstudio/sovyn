from collections import defaultdict
from random import Random

from ml.datasets.schemas import DatasetExample, TaskName


def stratified_sample(examples: tuple[DatasetExample, ...], sample: int | None, seed: int) -> tuple[DatasetExample, ...]:
    if sample is None or sample >= len(examples):
        return examples
    buckets: dict[TaskName, list[DatasetExample]] = defaultdict(list)
    for example in examples:
        buckets[example.task].append(example)
    rng = Random(seed)
    for values in buckets.values():
        rng.shuffle(values)
    per_task = max(sample // len(buckets), 1)
    selected: list[DatasetExample] = []
    for task in sorted(buckets, key=lambda item: item.value):
        selected.extend(buckets[task][:per_task])
    remaining = sample - len(selected)
    if remaining > 0:
        leftovers = tuple(example for values in buckets.values() for example in values[per_task:])
        selected.extend(leftovers[:remaining])
    return tuple(selected[:sample])
