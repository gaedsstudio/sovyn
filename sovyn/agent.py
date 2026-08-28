from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import anyio

from sovyn.providers import ModelProvider
from sovyn.sessions import create_session
from sovyn.storage import Store, record_trajectory
from sovyn.tools import ToolResult, git_status, list_files
from sovyn.ui import DiamondState, Renderer


@dataclass(frozen=True, slots=True)
class AgentResult:
    session_id: int
    response: str
    tools: tuple[ToolResult, ...]
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class AgentRuntime:
    provider: ModelProvider
    store: Store
    renderer: Renderer
    workspace: Path


def run_agent(request: str, runtime: AgentRuntime) -> AgentResult:
    started = perf_counter()
    runtime.renderer.line(DiamondState.WAITING, "Reading workspace...")
    tools = (list_files(runtime.workspace), git_status(runtime.workspace))
    runtime.renderer.line(DiamondState.COMPLETED, tools[0].summary)
    runtime.renderer.line(DiamondState.WAITING, "Planning next action...")
    response = anyio.run(runtime.provider.generate, request)
    duration = perf_counter() - started
    session_id = create_session(runtime.store, request, "success", len(tools), duration)
    record_trajectory(runtime.store, session_id, tools)
    runtime.renderer.line(DiamondState.COMPLETED, "Session recorded")
    return AgentResult(session_id=session_id, response=response, tools=tools, duration_seconds=duration)
