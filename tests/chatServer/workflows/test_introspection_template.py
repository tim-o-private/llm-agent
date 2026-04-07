"""Tests for SPEC-040 introspection workflow template parsing and step validation."""


from chatServer.workflows.template_parser import parse_template
from chatServer.workflows.templates.introspection import (
    PROMPT_ANALYZE_PATTERNS,
    PROMPT_APPLY_CHANGES,
    PROMPT_GATHER_SIGNALS,
    PROMPT_PROPOSE_CHANGES,
    TEMPLATE,
)


class TestIntrospectionTemplate:
    def test_parses_successfully(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        assert tpl.name == "introspection-loop"
        assert tpl.version == 1
        assert tpl.default_gate_policy == "none"

    def test_has_four_steps(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        assert len(tpl.steps) == 4

    def test_step_names(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        names = [s.name for s in tpl.steps]
        assert names == ["gather-signals", "analyze-patterns", "propose-changes", "apply-changes"]

    def test_gather_signals_is_service_node(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        gather = tpl.steps[0]
        assert gather.node_type == "service"
        assert gather.agent == "signal-gatherer"
        assert gather.depends_on == []
        assert gather.gate_policy == "none"

    def test_gather_signals_tools(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        gather = tpl.steps[0]
        assert "search_memories" in gather.tools
        assert "read_file" in gather.tools
        assert "list_files" in gather.tools

    def test_analyze_patterns_uses_sonnet(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        analyze = tpl.steps[1]
        assert analyze.model == "claude-sonnet-4-5-20250514"
        assert analyze.tools == []
        assert analyze.depends_on == ["gather-signals"]
        assert analyze.gate_policy == "none"

    def test_propose_changes_uses_sonnet(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        propose = tpl.steps[2]
        assert propose.model == "claude-sonnet-4-5-20250514"
        assert propose.tools == []
        assert propose.depends_on == ["analyze-patterns"]
        assert propose.gate_policy == "none"

    def test_apply_changes_is_service_node(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        apply_step = tpl.steps[3]
        assert apply_step.node_type == "service"
        assert apply_step.depends_on == ["propose-changes"]
        assert apply_step.gate_policy == "dynamic"

    def test_apply_changes_tools(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        apply_step = tpl.steps[3]
        assert "write_file" in apply_step.tools
        assert "read_file" in apply_step.tools

    def test_parameters(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        param_names = [p.name for p in tpl.parameters]
        assert "period_days" in param_names
        assert "focus_areas" in param_names
        assert "trust_tier" in param_names

    def test_trust_tier_required(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        trust_param = next(p for p in tpl.parameters if p.name == "trust_tier")
        assert trust_param.required

    def test_period_days_optional(self):
        tpl = parse_template(TEMPLATE, "introspection-loop")
        period_param = next(p for p in tpl.parameters if p.name == "period_days")
        assert not period_param.required


class TestIntrospectionStepPrompts:
    def test_gather_signals_prompt_has_sections(self):
        assert "User Feedback" in PROMPT_GATHER_SIGNALS
        assert "Current Config" in PROMPT_GATHER_SIGNALS
        assert "Interaction History" in PROMPT_GATHER_SIGNALS
        assert "Output Format" in PROMPT_GATHER_SIGNALS

    def test_analyze_patterns_prompt_has_antipatterns(self):
        assert "Anti-Patterns" in PROMPT_ANALYZE_PATTERNS
        assert "Do not propose changes based on a single interaction" in PROMPT_ANALYZE_PATTERNS
        assert "rejected_proposals.md" in PROMPT_ANALYZE_PATTERNS

    def test_analyze_patterns_has_categories(self):
        assert "What's Working" in PROMPT_ANALYZE_PATTERNS
        assert "What's Degraded" in PROMPT_ANALYZE_PATTERNS
        assert "What's Missing" in PROMPT_ANALYZE_PATTERNS
        assert "Capability Gaps" in PROMPT_ANALYZE_PATTERNS

    def test_propose_changes_has_max_limit(self):
        assert "Maximum 3 proposals" in PROMPT_PROPOSE_CHANGES

    def test_propose_changes_has_format(self):
        assert "file_path" in PROMPT_PROPOSE_CHANGES
        assert "change_type" in PROMPT_PROPOSE_CHANGES
        assert "diff_preview" in PROMPT_PROPOSE_CHANGES
        assert "rationale" in PROMPT_PROPOSE_CHANGES
        assert "expected_impact" in PROMPT_PROPOSE_CHANGES
        assert "risk" in PROMPT_PROPOSE_CHANGES
        assert "elevated" in PROMPT_PROPOSE_CHANGES

    def test_propose_changes_has_capability_request_format(self):
        assert "capability_request" in PROMPT_PROPOSE_CHANGES
        assert "tool_name" in PROMPT_PROPOSE_CHANGES

    def test_apply_changes_has_rules(self):
        assert "/user/" in PROMPT_APPLY_CHANGES
        assert "/system/" in PROMPT_APPLY_CHANGES
        assert "rejected" in PROMPT_APPLY_CHANGES
        assert "elevated" in PROMPT_APPLY_CHANGES
