import json

from ml.datasets.schemas import DatasetExample
from ml.inference.chat import training_messages_for_example


def format_sft_record(example: DatasetExample) -> str:
    messages = tuple({"role": message.role, "content": message.content} for message in training_messages_for_example(example))
    return json.dumps({"messages": messages}, ensure_ascii=False)
