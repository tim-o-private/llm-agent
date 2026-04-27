"""Tests for SPEC-037 workflow template parsing and step validation."""

import pytest

from chatServer.workflows.template_parser import parse_template
from chatServer.workflows.templates.draft_reply import TEMPLATE as DRAFT_REPLY
from chatServer.workflows.templates.email_triage import TEMPLATE as EMAIL_TRIAGE
from chatServer.workflows.templates.evening_briefing import TEMPLATE as EVENING_BRIEFING
from chatServer.workflows.templates.morning_briefing import TEMPLATE as MORNING_BRIEFING

# --- email-triage ---


class TestEmailTriageTemplate:
    def test_parses_successfully(self):
        tpl = parse_template(EMAIL_TRIAGE, "email-triage")
        assert tpl.name == "email-triage"
        assert tpl.version == 1
        assert tpl.default_gate_policy == "none"

    def test_has_three_steps(self):
        tpl = parse_template(EMAIL_TRIAGE, "email-triage")
        assert len(tpl.steps) == 3

    def test_step_names(self):
        tpl = parse_template(EMAIL_TRIAGE, "email-triage")
        names = [s.name for s in tpl.steps]
        assert names == ["fetch-emails", "categorize", "summarize"]

    def test_fetch_emails_tools(self):
        tpl = parse_template(EMAIL_TRIAGE, "email-triage")
        fetch = tpl.steps[0]
        assert fetch.tools == ["search_gmail", "get_gmail"]
        assert fetch.depends_on == []

    def test_categorize_uses_openai_mini(self):
        tpl = parse_template(EMAIL_TRIAGE, "email-triage")
        categorize = tpl.steps[1]
        assert categorize.model == "openai:gpt-4o-mini"
        assert categorize.tools == []
        assert categorize.depends_on == ["fetch-emails"]

    def test_summarize_has_memory_tool(self):
        tpl = parse_template(EMAIL_TRIAGE, "email-triage")
        summarize = tpl.steps[2]
        assert summarize.tools == ["create_memories"]
        assert summarize.depends_on == ["categorize"]

    def test_all_gates_none(self):
        tpl = parse_template(EMAIL_TRIAGE, "email-triage")
        for step in tpl.steps:
            assert step.gate_policy == "none"

    def test_parameters(self):
        tpl = parse_template(EMAIL_TRIAGE, "email-triage")
        param_names = [p.name for p in tpl.parameters]
        assert "hours_back" in param_names
        assert "max_emails" in param_names
        for p in tpl.parameters:
            assert not p.required


# --- morning-briefing ---


class TestMorningBriefingTemplate:
    def test_parses_successfully(self):
        tpl = parse_template(MORNING_BRIEFING, "morning-briefing")
        assert tpl.name == "morning-briefing"

    def test_has_three_steps(self):
        tpl = parse_template(MORNING_BRIEFING, "morning-briefing")
        assert len(tpl.steps) == 3

    def test_step_names(self):
        tpl = parse_template(MORNING_BRIEFING, "morning-briefing")
        names = [s.name for s in tpl.steps]
        assert names == ["gather-context", "compose-briefing", "deliver"]

    def test_gather_context_tools(self):
        tpl = parse_template(MORNING_BRIEFING, "morning-briefing")
        gather = tpl.steps[0]
        assert "search_calendar" in gather.tools
        assert "get_tasks" in gather.tools
        assert "search_gmail" in gather.tools
        assert "search_memories" in gather.tools

    def test_deliver_is_service_node(self):
        tpl = parse_template(MORNING_BRIEFING, "morning-briefing")
        deliver = tpl.steps[2]
        assert deliver.node_type == "service"
        assert deliver.tools == []

    def test_timezone_required(self):
        tpl = parse_template(MORNING_BRIEFING, "morning-briefing")
        tz_param = next(p for p in tpl.parameters if p.name == "timezone")
        assert tz_param.required


# --- evening-briefing ---


class TestEveningBriefingTemplate:
    def test_parses_successfully(self):
        tpl = parse_template(EVENING_BRIEFING, "evening-briefing")
        assert tpl.name == "evening-briefing"

    def test_has_three_steps(self):
        tpl = parse_template(EVENING_BRIEFING, "evening-briefing")
        assert len(tpl.steps) == 3

    def test_deliver_is_service_node(self):
        tpl = parse_template(EVENING_BRIEFING, "evening-briefing")
        deliver = tpl.steps[2]
        assert deliver.node_type == "service"

    def test_step_names(self):
        tpl = parse_template(EVENING_BRIEFING, "evening-briefing")
        names = [s.name for s in tpl.steps]
        assert names == ["gather-context", "compose-briefing", "deliver"]


# --- draft-reply ---


class TestDraftReplyTemplate:
    def test_parses_successfully(self):
        tpl = parse_template(DRAFT_REPLY, "draft-reply")
        assert tpl.name == "draft-reply"
        assert tpl.default_gate_policy == "escalation-only"

    def test_has_four_steps(self):
        tpl = parse_template(DRAFT_REPLY, "draft-reply")
        assert len(tpl.steps) == 4

    def test_step_names(self):
        tpl = parse_template(DRAFT_REPLY, "draft-reply")
        names = [s.name for s in tpl.steps]
        assert names == ["fetch-context", "compose-draft", "present-for-approval", "send"]

    def test_fetch_context_tools(self):
        tpl = parse_template(DRAFT_REPLY, "draft-reply")
        fetch = tpl.steps[0]
        assert fetch.tools == ["get_gmail", "search_memories"]

    def test_present_for_approval_is_gate(self):
        tpl = parse_template(DRAFT_REPLY, "draft-reply")
        approval = tpl.steps[2]
        assert approval.node_type == "gate"
        assert approval.gate_policy == "human-required"

    def test_send_step_tools(self):
        tpl = parse_template(DRAFT_REPLY, "draft-reply")
        send = tpl.steps[3]
        assert send.tools == ["send_email_reply"]
        assert send.depends_on == ["present-for-approval"]

    def test_required_parameters(self):
        tpl = parse_template(DRAFT_REPLY, "draft-reply")
        required = [p.name for p in tpl.parameters if p.required]
        assert "message_id" in required
        assert "account" in required

    def test_instructions_optional(self):
        tpl = parse_template(DRAFT_REPLY, "draft-reply")
        instructions = next(p for p in tpl.parameters if p.name == "instructions")
        assert not instructions.required


# --- Service node type in builder ---


class TestServiceNodeInBuilder:
    def test_builder_raises_for_unregistered_service(self):
        """GraphBuilder should raise if a service step has no registered function."""
        from unittest.mock import MagicMock

        from chatServer.workflows.builder import GraphBuilder

        tpl = parse_template(MORNING_BRIEFING, "morning-briefing")
        engine = MagicMock()
        builder = GraphBuilder()  # No services registered

        with pytest.raises(ValueError, match="No service registered"):
            builder.build(tpl, engine)

    def test_builder_accepts_registered_service(self):
        """GraphBuilder should build successfully when service is registered."""
        from unittest.mock import AsyncMock, MagicMock

        from chatServer.workflows.builder import GraphBuilder

        tpl = parse_template(MORNING_BRIEFING, "morning-briefing")
        engine = MagicMock()
        builder = GraphBuilder(service_registry={"deliver": AsyncMock(return_value="ok")})

        compiled, interrupt_nodes = builder.build(tpl, engine)
        assert compiled is not None
        assert interrupt_nodes == []

    def test_run_manager_registers_all_service_nodes(self):
        """WorkflowRunManager must register services for every template that uses service-type steps.

        This is an integration test that catches regressions like SPEC-044
        removing service registrations. It builds every template that contains
        a service node through the RunManager's builder — if any service step
        is unregistered, the build raises ValueError.
        """
        from unittest.mock import MagicMock

        from chatServer.workflows.run_manager import WorkflowRunManager

        manager = WorkflowRunManager(
            db_client=MagicMock(),
            anthropic_client=MagicMock(),
            tool_schemas=[],
            tool_executors={},
        )
        engine = MagicMock()

        service_templates = [
            (MORNING_BRIEFING, "morning-briefing"),
            (EVENING_BRIEFING, "evening-briefing"),
        ]
        for template_md, name in service_templates:
            tpl = parse_template(template_md, name)
            # Raises ValueError if a service step is unregistered
            compiled, _ = manager._builder.build(tpl, engine)
            assert compiled is not None, f"{name} failed to build"
