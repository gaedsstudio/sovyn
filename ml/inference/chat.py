import json
from dataclasses import dataclass

from ml.datasets.schemas import DatasetExample
from ml.prompts.sovyn import SOVYN_SYSTEM_PROMPT


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


def messages_for_example(example: DatasetExample) -> tuple[ChatMessage, ...]:
    user_payload = {
        "task": example.task.value,
        "instruction": example.instruction,
        "input": example.input,
    }
    return (
        ChatMessage("system", SOVYN_SYSTEM_PROMPT),
        ChatMessage("user", json.dumps(user_payload, ensure_ascii=False)),
    )


def training_messages_for_example(example: DatasetExample) -> tuple[ChatMessage, ...]:
    return messages_for_example(example) + (ChatMessage("assistant", example.output),)


def strip_reasoning_text(value: str) -> str:
    end_tag = "</think>"
    if end_tag not in value:
        return value.strip()
    return value.split(end_tag, maxsplit=1)[1].strip()
