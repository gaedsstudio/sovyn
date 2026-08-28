from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompressionConfig:
    max_lines: int = 80
    edge_lines: int = 20


def compress_text(value: str, config: CompressionConfig = CompressionConfig()) -> str:
    lines = value.splitlines()
    if len(lines) <= config.max_lines:
        return value
    omitted = len(lines) - (config.edge_lines * 2)
    head = lines[: config.edge_lines]
    tail = lines[-config.edge_lines :]
    return "\n".join((*head, f"[output truncated: {omitted} lines omitted]", *tail))
