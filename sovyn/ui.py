from dataclasses import dataclass
from enum import StrEnum, unique
import os
from typing import TextIO


@unique
class DiamondState(StrEnum):
    WAITING = "◇"
    WORKING = "◈"
    COMPLETED = "◆"
    ATTENTION = "!"
    FAILED = "×"


FRAMES = (DiamondState.WAITING.value, DiamondState.WORKING.value, DiamondState.COMPLETED.value, DiamondState.WORKING.value)


@dataclass(frozen=True, slots=True)
class TerminalCapabilities:
    interactive: bool
    color: bool


class Renderer:
    def __init__(self, stream: TextIO, interactive: bool | None = None, color: bool | None = None) -> None:
        self.stream = stream
        self.capabilities = TerminalCapabilities(
            interactive=stream.isatty() if interactive is None else interactive,
            color=("NO_COLOR" not in os.environ) if color is None else color,
        )

    def line(self, state: DiamondState, message: str) -> None:
        self.stream.write(f"{state.value} {message}\n")
        self.stream.flush()

    def update(self, frame_index: int, message: str) -> None:
        frame = FRAMES[frame_index % len(FRAMES)]
        if self.capabilities.interactive:
            self.stream.write(f"\r{frame} {message}")
        else:
            self.stream.write(f"{DiamondState.WORKING.value} {message}\n")
        self.stream.flush()

    def complete(self, message: str) -> None:
        if self.capabilities.interactive:
            self.stream.write("\r")
        self.line(DiamondState.COMPLETED, message)
