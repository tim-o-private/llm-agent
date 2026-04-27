"""GraphBuilder — convert a GraphTemplate into a compiled LangGraph StateGraph.

Each template step becomes a node. depends_on determines edges.
Steps with gate_policy: "human-required" get interrupt_before set.
"""

import logging
from typing import Any, Callable, Optional, TypedDict

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from chatServer.config.settings import get_settings
from .engine import AnthropicEngine
from .models import GraphTemplate, StepDef

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict, total=False):
    """State shared across all nodes in a workflow graph."""
    messages: list[dict]
    step_outputs: dict[str, str]
    parameters: dict[str, Any]
    current_step: str
    status: str
    approval: Optional[dict]
    revision_count: int


def _default_state() -> WorkflowState:
    """Create a default initial state."""
    return WorkflowState(
        messages=[],
        step_outputs={},
        parameters={},
        current_step="",
        status="running",
        approval=None,
        revision_count=0,
    )


ServiceFn = Callable[[WorkflowState], Any]
PromptLoaderFn = Callable[[str, str], Any]  # (template_name, step_name) -> Optional[str]


class GraphBuilder:
    """Build a LangGraph StateGraph from a GraphTemplate."""

    def __init__(
        self,
        service_registry: Optional[dict[str, ServiceFn]] = None,
        prompt_loader: Optional[PromptLoaderFn] = None,
    ):
        self._service_registry: dict[str, ServiceFn] = service_registry or {}
        self._prompt_loader = prompt_loader

    def register_service(self, step_name: str, fn: ServiceFn) -> None:
        """Register a service function for a service-type step."""
        self._service_registry[step_name] = fn

    def build(
        self,
        template: GraphTemplate,
        engine: AnthropicEngine,
        checkpointer: Any = None,
    ) -> tuple[Any, list[str]]:
        """Build and compile a StateGraph from the template.

        Args:
            template: Parsed graph template.
            engine: AnthropicEngine for step execution.
            checkpointer: Optional LangGraph checkpointer for state persistence.

        Returns:
            (compiled_graph, interrupt_node_names)
        """
        graph = StateGraph(WorkflowState)
        interrupt_nodes: list[str] = []

        # Add nodes for each step
        for step in template.steps:
            if step.node_type == "service":
                node_fn = self._make_service_node(step)
            else:
                node_fn = self._make_step_node(step, engine, template)
            graph.add_node(step.name, node_fn)

            if step.gate_policy == "human-required":
                gate_fn = self._make_gate_node(step)
                gate_name = f"{step.name}_gate"
                graph.add_node(gate_name, gate_fn)
                interrupt_nodes.append(gate_name)

        # Wire edges based on depends_on
        for step in template.steps:
            if not step.depends_on:
                graph.add_edge(START, step.name)
            else:
                for dep_name in step.depends_on:
                    dep_step = self._find_step(template, dep_name)
                    if dep_step and dep_step.gate_policy == "human-required":
                        graph.add_edge(f"{dep_name}_gate", step.name)
                    else:
                        graph.add_edge(dep_name, step.name)

            # If this step has a gate, add edge from step to gate
            if step.gate_policy == "human-required":
                graph.add_edge(step.name, f"{step.name}_gate")

        # Terminal nodes → END
        terminal_steps = self._find_terminal_steps(template)
        for step in terminal_steps:
            if step.gate_policy == "human-required":
                graph.add_edge(f"{step.name}_gate", END)
            else:
                graph.add_edge(step.name, END)

        compiled = graph.compile(
            checkpointer=checkpointer,
            interrupt_before=interrupt_nodes if interrupt_nodes else None,
        )
        return compiled, interrupt_nodes

    def _make_step_node(
        self, step: StepDef, engine: AnthropicEngine, template: GraphTemplate
    ):
        """Create a closure for a step node."""
        prompt_loader = self._prompt_loader

        async def step_node(state: WorkflowState) -> dict:
            # Load system prompt from config if available
            system_prompt = None
            if prompt_loader:
                try:
                    system_prompt = await prompt_loader(template.name, step.name)
                except Exception:
                    logger.warning(
                        "Failed to load prompt for %s/%s, using description",
                        template.name, step.name,
                    )

            # Fall back to step description as system prompt
            if not system_prompt:
                system_prompt = step.description

            # Assemble user prompt from prior outputs + parameters
            prompt_parts = [step.description]

            # Include prior step outputs
            step_outputs = state.get("step_outputs", {})
            if step_outputs:
                prompt_parts.append("\n## Prior step results:")
                for dep_name in step.depends_on:
                    slug = self._resolve_slug(template, dep_name)
                    if slug in step_outputs:
                        prompt_parts.append(f"\n### {dep_name}:\n{step_outputs[slug]}")

            # Include parameters
            params = state.get("parameters", {})
            if params:
                prompt_parts.append(
                    "\n## Workflow parameters:\n"
                    + "\n".join(f"- {k}: {v}" for k, v in params.items())
                )

            prompt = "\n".join(prompt_parts)

            settings = get_settings()
            # Run engine with step-specific config and system prompt
            result = await engine.run(
                prompt=prompt,
                tools=step.tools,
                system_prompt=system_prompt,
                model=step.model or settings.llm_default_model,
                max_tokens=step.max_tokens or 4096,
                temperature=step.temperature if step.temperature is not None else 0.5,
            )

            # Update state
            new_outputs = dict(step_outputs)
            new_outputs[step.name] = result.output

            return {
                "step_outputs": new_outputs,
                "current_step": step.name,
                "status": "running",
            }

        step_node.__name__ = f"step_{step.name}"
        return step_node

    def _make_service_node(self, step: StepDef):
        """Create a node that calls a registered service function, not the LLM."""
        service_fn = self._service_registry.get(step.name)
        if not service_fn:
            raise ValueError(f"No service registered for step '{step.name}'")

        async def service_node(state: WorkflowState) -> dict:
            result = await service_fn(state)
            step_outputs = dict(state.get("step_outputs", {}))
            step_outputs[step.name] = str(result)
            return {
                "step_outputs": step_outputs,
                "current_step": step.name,
                "status": "running",
            }

        service_node.__name__ = f"service_{step.name}"
        return service_node

    def _make_gate_node(self, step: StepDef):
        """Create a gate node that signals approval is needed."""

        async def gate_node(state: WorkflowState) -> dict:
            return {
                "status": "waiting_for_approval",
                "current_step": f"{step.name}_gate",
            }

        gate_node.__name__ = f"gate_{step.name}"
        return gate_node

    def _find_step(self, template: GraphTemplate, name: str) -> Optional[StepDef]:
        """Find a step by its depends_on name (e.g., 'step-1')."""
        # depends_on uses raw step references (e.g., "step-1")
        # but step.name is slugified from the display name
        # Try exact match first, then check by original reference
        for step in template.steps:
            if step.name == name:
                return step
        return None

    def _resolve_slug(self, template: GraphTemplate, dep_name: str) -> str:
        """Resolve a depends_on reference to a step slug name."""
        step = self._find_step(template, dep_name)
        return step.name if step else dep_name

    def _find_terminal_steps(self, template: GraphTemplate) -> list[StepDef]:
        """Find steps that no other step depends on."""
        depended_on = set()
        for step in template.steps:
            for dep in step.depends_on:
                depended_on.add(dep)
        return [s for s in template.steps if s.name not in depended_on]
