from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdapterInferenceRequest:
    adapter_path: str
    context: str


def format_adapter_prompt(request: AdapterInferenceRequest) -> str:
    return (
        "Use only supplied SOVYN evidence.\n"
        "Separate FACT, INTERPRETATION, and UNCERTAINTY.\n"
        f"Context:\n{request.context}\n"
        f"Adapter:\n{request.adapter_path}"
    )

