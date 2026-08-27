import gzip
from pathlib import Path

import pytest

from sovyn_training.datasets.dedup import deduplicate_samples
from sovyn_training.datasets.streaming import ChatSample, stream_jsonl
from sovyn_training.errors import DatasetFormatError


def test_stream_jsonl_when_sample_limit_is_set(tmp_path: Path) -> None:
    path = tmp_path / "samples.jsonl"
    path.write_text(
        (
            '{"messages":[{"role":"user","content":"a"}]}\n'
            '{"messages":[{"role":"user","content":"b"}]}'
        ),
        encoding="utf-8",
    )

    samples = list(stream_jsonl(path, max_samples=1))

    assert len(samples) == 1
    assert samples[0]["messages"][0]["content"] == "a"


def test_stream_jsonl_when_gzip_file_is_used(tmp_path: Path) -> None:
    path = tmp_path / "samples.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write('{"messages":[{"role":"user","content":"compressed"}]}\n')

    samples = list(stream_jsonl(path))

    assert samples[0]["messages"][0]["content"] == "compressed"


def test_stream_jsonl_when_line_is_invalid(tmp_path: Path) -> None:
    path = tmp_path / "samples.jsonl"
    path.write_text("{invalid}\n", encoding="utf-8")

    with pytest.raises(DatasetFormatError):
        list(stream_jsonl(path))


def test_deduplicate_samples_when_content_repeats() -> None:
    sample = ChatSample(messages=[{"role": "user", "content": "same"}])
    other = ChatSample(messages=[{"role": "user", "content": "different"}])

    samples = list(deduplicate_samples([sample, sample, other]))

    assert samples == [sample, other]
