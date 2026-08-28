from enum import StrEnum, unique

from pydantic import BaseModel, ConfigDict, Field


@unique
class TrajectoryStepKind(StrEnum):
    DETERMINISTIC = "deterministic"
    AGENT_REQUIRED = "agent-required"
    USER_REQUIRED = "user-required"


class WorkflowStepSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: str
    kind: TrajectoryStepKind
    summary: str = ""


class WorkflowSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    description: str = ""
    manual: bool = True
    steps: tuple[WorkflowStepSchema, ...]


class SessionSummarySchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    request: str
    result: str
    tool_calls: int
    duration_seconds: float
