import gzip
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO, TypedDict

from sovyn_training.errors import DatasetFormatError, ZstdDependencyError


class Message(TypedDict):
    role: str
    content: str


class ChatSample(TypedDict):
    messages: list[Message]


@contextmanager
def _open_text_stream(path: Path) -> Iterator[TextIO]:
    match path.suffix:
        case ".gz":
            with gzip.open(path, mode="rt", encoding="utf-8") as handle:
                yield handle
        case ".zst":
            try:
                import zstandard
            except ModuleNotFoundError as exc:
                raise ZstdDependencyError(path=path) from exc
            with (
                path.open("rb") as raw,
                zstandard.open(raw, mode="rt", encoding="utf-8") as handle,
            ):
                yield handle
        case _:
            with path.open("rt", encoding="utf-8") as handle:
                yield handle


def stream_jsonl(path: Path, max_samples: int | None = None) -> Iterator[ChatSample]:
    yielded = 0
    with _open_text_stream(path) as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if line == "":
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetFormatError(path=path, line_number=line_number) from exc
            sample = ChatSample(messages=parsed["messages"])
            yield sample
            yielded += 1
            if max_samples is not None and yielded >= max_samples:
                return
