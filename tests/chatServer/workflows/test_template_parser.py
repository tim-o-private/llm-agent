"""Tests for workflow template parser."""

import pytest

from chatServer.workflows.models import TemplateParseError
from chatServer.workflows.template_parser import parse_template

VALID_TEMPLATE = """\
---
name: email-triage
description: Scheduled email processing
version: 2
default_gate_policy: none
---

# Email Triage

Process recent emails.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| hours_back | no | How many hours of email to process |
| max_emails | no | Maximum emails to process |
| account_id | yes | Gmail account to use |

## Steps

### step-1: Fetch and Categorize
- **agent:** email-classifier
- **depends_on:** []
- **tools:** [search_gmail, get_gmail]
- **description:** Search recent emails, categorize each.
- **gate:** none

### step-2: Summarize and Surface
- **agent:** briefing-composer
- **depends_on:** [step-1]
- **tools:** [create_memories]
- **description:** Compose a summary from categorized emails.
- **gate:** none
"""

GATED_TEMPLATE = """\
---
name: draft-reply
description: Draft a reply to an email
version: 1
default_gate_policy: escalation-only
---

# Draft Reply

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| email_id | yes | Email to reply to |

## Steps

### step-1: Analyze Email
- **agent:** email-analyzer
- **depends_on:** []
- **tools:** [get_gmail]
- **description:** Read the email and determine context.
- **gate:** none

### step-2: Draft Response
- **agent:** email-writer
- **depends_on:** [step-1]
- **tools:** [compose_email]
- **description:** Draft a reply based on analysis.
- **gate_policy:** human-required
- **model:** claude-sonnet-4-20250514
- **max_tokens:** 8192
- **temperature:** 0.7
"""


class TestParseValidTemplate:
    def test_parses_frontmatter(self):
        template = parse_template(VALID_TEMPLATE, "email-triage")
        assert template.name == "email-triage"
        assert template.description == "Scheduled email processing"
        assert template.version == 2
        assert template.default_gate_policy == "none"

    def test_parses_parameters(self):
        template = parse_template(VALID_TEMPLATE, "email-triage")
        assert len(template.parameters) == 3
        assert template.parameters[0].name == "hours_back"
        assert template.parameters[0].required is False
        assert template.parameters[2].name == "account_id"
        assert template.parameters[2].required is True

    def test_parses_steps(self):
        template = parse_template(VALID_TEMPLATE, "email-triage")
        assert len(template.steps) == 2

    def test_step_name_slugified(self):
        template = parse_template(VALID_TEMPLATE, "email-triage")
        assert template.steps[0].name == "fetch-and-categorize"
        assert template.steps[1].name == "summarize-and-surface"

    def test_step_agent(self):
        template = parse_template(VALID_TEMPLATE, "email-triage")
        assert template.steps[0].agent == "email-classifier"
        assert template.steps[1].agent == "briefing-composer"

    def test_step_tools_list(self):
        template = parse_template(VALID_TEMPLATE, "email-triage")
        assert template.steps[0].tools == ["search_gmail", "get_gmail"]
        assert template.steps[1].tools == ["create_memories"]

    def test_step_depends_on(self):
        template = parse_template(VALID_TEMPLATE, "email-triage")
        assert template.steps[0].depends_on == []
        assert template.steps[1].depends_on == ["step-1"]

    def test_step_description(self):
        template = parse_template(VALID_TEMPLATE, "email-triage")
        assert "categorize" in template.steps[0].description.lower()

    def test_step_gate_defaults_none(self):
        template = parse_template(VALID_TEMPLATE, "email-triage")
        assert template.steps[0].gate is None
        assert template.steps[0].gate_policy == "none"


class TestParseGatedTemplate:
    def test_gate_policy_human_required(self):
        template = parse_template(GATED_TEMPLATE, "draft-reply")
        step2 = template.steps[1]
        assert step2.gate_policy == "human-required"

    def test_step_model_override(self):
        template = parse_template(GATED_TEMPLATE, "draft-reply")
        step2 = template.steps[1]
        assert step2.model == "claude-sonnet-4-20250514"
        assert step2.max_tokens == 8192
        assert step2.temperature == 0.7

    def test_step_without_model_has_none(self):
        template = parse_template(GATED_TEMPLATE, "draft-reply")
        step1 = template.steps[0]
        assert step1.model is None
        assert step1.max_tokens is None
        assert step1.temperature is None


class TestParseErrors:
    def test_missing_frontmatter(self):
        with pytest.raises(TemplateParseError, match="missing YAML frontmatter"):
            parse_template("# No frontmatter here", "bad")

    def test_invalid_yaml(self):
        content = "---\n: invalid: yaml: [[\n---\n# Template\n"
        with pytest.raises(TemplateParseError, match="invalid YAML"):
            parse_template(content, "bad-yaml")

    def test_missing_name_field(self):
        content = "---\ndescription: no name\n---\n# Template\n"
        with pytest.raises(TemplateParseError, match="missing required field 'name'"):
            parse_template(content, "no-name")

    def test_frontmatter_not_a_mapping(self):
        content = "---\n- just a list\n---\n# Template\n"
        with pytest.raises(TemplateParseError, match="must be a mapping"):
            parse_template(content, "list-fm")


class TestParseEdgeCases:
    def test_template_with_no_steps(self):
        content = "---\nname: empty\n---\n# Empty template\n"
        template = parse_template(content, "empty")
        assert template.name == "empty"
        assert template.steps == []

    def test_template_with_no_parameters(self):
        content = "---\nname: no-params\n---\n# No params\n## Steps\n### step-1: Do Thing\n- **agent:** worker\n"
        template = parse_template(content, "no-params")
        assert template.parameters == []
        assert len(template.steps) == 1

    def test_empty_tools_list(self):
        content = "---\nname: t\n---\n## Steps\n### step-1: Work\n- **tools:** []\n"
        template = parse_template(content, "t")
        assert template.steps[0].tools == []

    def test_version_defaults_to_1(self):
        content = "---\nname: t\n---\n# T\n"
        template = parse_template(content, "t")
        assert template.version == 1
