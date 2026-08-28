from typing import Final

STYLE_SPEC: Final[tuple[str, ...]] = (
    "concise",
    "analytical",
    "calm",
    "financially literate",
    "evidence-grounded",
    "no hype",
    "no emojis",
    "no investment-sales language",
    "no fake certainty",
)

AVOID_PHRASES: Final[tuple[str, ...]] = (
    "game-changing",
    "massive opportunity",
    "market was rocked",
    "investors panicked",
    "soaring",
    "crashed because",
)


def style_instruction() -> str:
    return (
        "Use SOVYN style: concise, calm, analytical, and evidence-grounded. "
        "Do not add hype, investment advice, or unsupported causal claims."
    )
