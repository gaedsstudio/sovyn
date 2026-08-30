import json
from dataclasses import dataclass, field

from sovyn.tool_protocol import ToolCall
from sovyn.tools import ToolResult

READ_CACHEABLE_TOOLS = frozenset(
    ("filesystem.list", "filesystem.read", "workspace.search", "git.status", "git.diff", "git.log")
)
MUTATING_TOOLS = frozenset(
    ("filesystem.write", "filesystem.move", "filesystem.delete", "shell.run", "git.commit", "git.checkout", "git.clean")
)
CACHED_REPEAT_FEEDBACK = (
    "The identical read-only tool call already succeeded and its result is available in Tool observations.\n"
    "Do not request it again.\n"
    "Use the existing observation and continue toward completing the user's task."
)
CACHED_STALL_MESSAGE = "Model stalled on an already satisfied read-only action."
MAX_IDENTICAL_CACHE_REUSES = 1


@dataclass(slots=True)  # noqa: MUTABLE_OK
class ToolCallCache:
    revision: int = 0
    results: dict[tuple[int, str, str], ToolResult] = field(default_factory=dict)

    def result_for(self, call: ToolCall) -> ToolResult | None:
        return self.results.get(self._key(call))

    def store(self, call: ToolCall, result: ToolResult) -> None:
        if result.success and call.name in READ_CACHEABLE_TOOLS:
            self.results[self._key(call)] = result

    def observe(self, result: ToolResult) -> None:
        if result.name in MUTATING_TOOLS and not result.no_change:
            self.revision += 1
            self.results.clear()

    def repeat_key(self, call: ToolCall) -> str:
        return f"{call.name}:{json.dumps(call.arguments, sort_keys=True, separators=(',', ':'))}"

    def _key(self, call: ToolCall) -> tuple[int, str, str]:
        return self.revision, call.name, json.dumps(call.arguments, sort_keys=True, separators=(",", ":"))


@dataclass(slots=True)  # noqa: MUTABLE_OK
class CachedRepeatGuard:
    key: str = ""
    count: int = 0

    def observe(self, key: str) -> str | None:
        if key == self.key:
            self.count += 1
        else:
            self.key = key
            self.count = 1
        if self.count == MAX_IDENTICAL_CACHE_REUSES:
            return CACHED_REPEAT_FEEDBACK
        if self.count > MAX_IDENTICAL_CACHE_REUSES:
            return CACHED_STALL_MESSAGE
        return None

    def reset(self) -> None:
        self.key = ""
        self.count = 0
