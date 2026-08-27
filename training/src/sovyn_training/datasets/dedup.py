import hashlib
import json
from collections.abc import Iterable, Iterator

from sovyn_training.datasets.streaming import ChatSample


def sample_hash(sample: ChatSample) -> str:
    normalized = json.dumps(
        sample,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def deduplicate_samples(samples: Iterable[ChatSample]) -> Iterator[ChatSample]:
    seen: set[str] = set()
    for sample in samples:
        digest = sample_hash(sample)
        if digest in seen:
            continue
        seen.add(digest)
        yield sample
