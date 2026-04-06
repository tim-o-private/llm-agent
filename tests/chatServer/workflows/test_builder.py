"""Tests for GraphBuilder — template to compiled StateGraph."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.workflows.builder import GraphBuilder
from chatServer.workflows.engine import AnthropicEngine
from chatServer.workflows.models import EngineResult, GraphTemplate, StepDef, TokenUsage


def _make_simple_template() -> GraphTemplate:
    """Two-step linear template: step-1 → step-2."""
    return GraphTemplate(
        name="test-workflow",
        description="Test",
        version=1,
        steps=[
            StepDef(
                name="step-1",
                agent="worker-a",
                depends_on=[],
                description="First step",
                tools=["tool_a"],
            ),
            StepDef(
                name="step-2",
                agent="worker-b",
                depends_on=["step-1"],
                description="Second step",
                tools=["tool_b"],
            ),
        ],
    )


def _make_gated_template() -> GraphTemplate:
    """Template with a human gate on step-2."""
    return GraphTemplate(
        name="gated-workflow",
        description="Test with gate",
        version=1,
        steps=[
            StepDef(
                name="step-1",
                agent="analyzer",
                depends_on=[],
                description="Analyze",
                tools=[],
            ),
            StepDef(
                name="step-2",
                agent="writer",
                depends_on=["step-1"],
                description="Write draft",
                tools=[],
                gate_policy="human-required",
            ),
        ],
    )


def _make_mock_engine() -> AnthropicEngine:
    """Create a mock engine that returns canned results."""
    engine = MagicMock(spec=AnthropicEngine)
    engine.run = AsyncMock(return_value=EngineResult(
        output="Step completed.",
        tool_calls=[],
        token_usage=TokenUsage(input_tokens=50, output_tokens=25),
    ))
    return engine


class TestBuildSimpleGraph:
    def test_compiles_without_error(self):
        builder = GraphBuilder()
        template = _make_simple_template()
        engine = _make_mock_engine()
        compiled, interrupts = builder.build(template, engine)
        assert compiled is not None
        assert interrupts == []

    @pytest.mark.asyncio
    async def test_executes_linear_graph(self):
        builder = GraphBuilder()
        template = _make_simple_template()
        engine = _make_mock_engine()
        compiled, _ = builder.build(template, engine)

        initial_state = {
            "messages": [],
            "step_outputs": {},
            "parameters": {"test_param": "value"},
            "current_step": "",
            "status": "running",
            "approval": None,
        }

        result = await compiled.ainvoke(initial_state)
        assert "step-1" in result["step_outputs"]
        assert "step-2" in result["step_outputs"]
        assert result["step_outputs"]["step-1"] == "Step completed."
        assert result["step_outputs"]["step-2"] == "Step completed."

    @pytest.mark.asyncio
    async def test_engine_called_with_step_tools(self):
        builder = GraphBuilder()
        template = _make_simple_template()
        engine = _make_mock_engine()
        compiled, _ = builder.build(template, engine)

        await compiled.ainvoke({
            "messages": [],
            "step_outputs": {},
            "parameters": {},
            "current_step": "",
            "status": "running",
            "approval": None,
        })

        # Engine should be called twice (once per step)
        assert engine.run.call_count == 2
        # First call should have tool_a
        first_call = engine.run.call_args_list[0]
        assert first_call.kwargs["tools"] == ["tool_a"]
        # Second call should have tool_b
        second_call = engine.run.call_args_list[1]
        assert second_call.kwargs["tools"] == ["tool_b"]


class TestBuildGatedGraph:
    def test_identifies_interrupt_nodes(self):
        builder = GraphBuilder()
        template = _make_gated_template()
        engine = _make_mock_engine()
        compiled, interrupts = builder.build(template, engine)
        assert "step-2_gate" in interrupts

    @pytest.mark.asyncio
    async def test_graph_pauses_at_gate(self):
        builder = GraphBuilder()
        template = _make_gated_template()
        engine = _make_mock_engine()

        # Use MemorySaver for checkpoint during test
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

        compiled, _ = builder.build(
            template, engine, checkpointer=checkpointer
        )

        config = {"configurable": {"thread_id": "test-thread"}}
        result = await compiled.ainvoke(
            {
                "messages": [],
                "step_outputs": {},
                "parameters": {},
                "current_step": "",
                "status": "running",
                "approval": None,
            },
            config,
        )

        # Graph should have paused before the gate node
        assert result["step_outputs"].get("step-1") == "Step completed."
        assert result["step_outputs"].get("step-2") == "Step completed."
        assert result["status"] == "running"


class TestBuildSingleStepGraph:
    def test_single_step(self):
        template = GraphTemplate(
            name="single",
            steps=[StepDef(name="only-step", description="Do it", tools=[])],
        )
        builder = GraphBuilder()
        engine = _make_mock_engine()
        compiled, interrupts = builder.build(template, engine)
        assert interrupts == []

    @pytest.mark.asyncio
    async def test_single_step_executes(self):
        template = GraphTemplate(
            name="single",
            steps=[StepDef(name="only-step", description="Do it", tools=[])],
        )
        builder = GraphBuilder()
        engine = _make_mock_engine()
        compiled, _ = builder.build(template, engine)

        result = await compiled.ainvoke({
            "messages": [],
            "step_outputs": {},
            "parameters": {},
            "current_step": "",
            "status": "running",
            "approval": None,
        })
        assert result["step_outputs"]["only-step"] == "Step completed."
