"""Workflow data models — GraphTemplate, StepDef, ParameterDef, state types."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class WorkflowRunStatus(str, Enum):
    """Status of a workflow run."""
    pending = "pending"
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


@dataclass
class ParameterDef:
    """A workflow parameter definition."""
    name: str
    required: bool = False
    description: str = ""
    default: Optional[str] = None


@dataclass
class StepDef:
    """A single step in a workflow template."""
    name: str
    agent: str = ""
    depends_on: list[str] = field(default_factory=list)
    description: str = ""
    tools: list[str] = field(default_factory=list)
    gate: Optional[str] = None
    gate_policy: str = "none"
    node_type: str = "engine"  # "engine" (LLM), "service" (Python fn), "gate" (human approval)
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


@dataclass
class GraphTemplate:
    """A parsed graph template."""
    name: str
    description: str = ""
    version: int = 1
    parameters: list[ParameterDef] = field(default_factory=list)
    steps: list[StepDef] = field(default_factory=list)
    default_gate_policy: str = "none"


@dataclass
class ToolCallRecord:
    """Record of a tool call during engine execution."""
    tool_name: str
    tool_call_id: str
    input: dict
    output: str
    is_error: bool = False


@dataclass
class TokenUsage:
    """Cumulative token usage."""
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class EngineResult:
    """Result of an AnthropicEngine step execution."""
    output: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)


class WorkflowState:
    """TypedDict-style state for LangGraph workflows.

    Defined as a dict schema for StateGraph compatibility:
    - messages: list — conversation history per step
    - step_outputs: dict[str, str] — accumulated results keyed by step name
    - parameters: dict — user-provided inputs
    - current_step: str — currently executing step
    - status: str — running/waiting_for_approval/completed/failed/cancelled
    - approval: dict | None — approval data from human gate
    """
    # This class exists for documentation. The actual state is a TypedDict
    # used in builder.py.
    pass


@dataclass
class WorkflowRunRecord:
    """Metadata for a workflow run (mirrors workflow_runs table)."""
    id: str
    user_id: str
    template_name: str
    thread_id: str
    status: WorkflowRunStatus
    parameters: dict[str, Any] = field(default_factory=dict)
    step_outputs: dict[str, str] = field(default_factory=dict)
    current_step: str = ""
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None


class TemplateParseError(Exception):
    """Raised when a workflow template cannot be parsed."""
    pass


class TemplateNotFoundError(Exception):
    """Raised when a workflow template is not found in the registry."""
    pass


class MissingParameterError(Exception):
    """Raised when required workflow parameters are missing."""
    def __init__(self, missing_params: list[str]):
        self.missing_params = missing_params
        super().__init__(f"Missing required parameters: {', '.join(missing_params)}")
