"""Template parser — Markdown+YAML frontmatter to GraphTemplate.

Parses the same format used by HQ's graph templates:
- YAML frontmatter for metadata (name, description, version, default_gate_policy)
- ## Parameters table
- ### step-N: Name sections with - **key:** value fields
"""

import logging
import re
from typing import Optional

import yaml

from .models import GraphTemplate, ParameterDef, StepDef, TemplateParseError

logger = logging.getLogger(__name__)

# Regex patterns
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_STEP_HEADER_RE = re.compile(r"^###\s+step-\d+:\s+(.+)$", re.MULTILINE)
_FIELD_RE = re.compile(r"^-\s+\*\*(\w+):\*\*\s+(.+)$", re.MULTILINE)
_PARAM_ROW_RE = re.compile(
    r"^\|\s*(\w+)\s*\|\s*(yes|no)\s*\|\s*(.*?)\s*\|$",
    re.MULTILINE | re.IGNORECASE,
)


def parse_template(content: str, source_name: str = "<unknown>") -> GraphTemplate:
    """Parse a Markdown workflow template into a GraphTemplate.

    Args:
        content: Raw Markdown content with YAML frontmatter.
        source_name: Template name/path for error messages.

    Returns:
        Parsed GraphTemplate.

    Raises:
        TemplateParseError: If the template is malformed.
    """
    # 1. Extract frontmatter
    fm_match = _FRONTMATTER_RE.search(content)
    if not fm_match:
        raise TemplateParseError(
            f"Template '{source_name}': missing YAML frontmatter"
        )

    try:
        frontmatter = yaml.safe_load(fm_match.group(1))
    except yaml.YAMLError as e:
        raise TemplateParseError(
            f"Template '{source_name}': invalid YAML frontmatter: {e}"
        )

    if not isinstance(frontmatter, dict):
        raise TemplateParseError(
            f"Template '{source_name}': frontmatter must be a mapping"
        )

    name = frontmatter.get("name")
    if not name:
        raise TemplateParseError(
            f"Template '{source_name}': missing required field 'name' in frontmatter"
        )

    # 2. Parse parameters table
    parameters = _parse_parameters(content)

    # 3. Parse steps
    steps = _parse_steps(content, source_name)

    default_gate_policy = frontmatter.get("default_gate_policy", "none")

    return GraphTemplate(
        name=name,
        description=frontmatter.get("description", ""),
        version=int(frontmatter.get("version", 1)),
        parameters=parameters,
        steps=steps,
        default_gate_policy=default_gate_policy,
    )


def _parse_parameters(content: str) -> list[ParameterDef]:
    """Parse the ## Parameters table into ParameterDef list."""
    params = []
    for match in _PARAM_ROW_RE.finditer(content):
        param_name = match.group(1)
        required = match.group(2).strip().lower() == "yes"
        description = match.group(3).strip()
        params.append(ParameterDef(
            name=param_name,
            required=required,
            description=description,
        ))
    return params


def _parse_steps(content: str, source_name: str) -> list[StepDef]:
    """Parse ### step-N: Name sections into StepDef list."""
    # Find all step headers and their positions
    headers = list(_STEP_HEADER_RE.finditer(content))
    if not headers:
        return []

    steps = []
    for i, header in enumerate(headers):
        step_name = header.group(1).strip()

        # Extract section body (from header to next header or end)
        start = header.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
        section = content[start:end]

        # Parse key-value fields
        fields = {}
        for field_match in _FIELD_RE.finditer(section):
            key = field_match.group(1).lower()
            value = field_match.group(2).strip()
            fields[key] = value

        step = StepDef(
            name=_slugify_step_name(step_name),
            agent=fields.get("agent", ""),
            depends_on=_parse_list_field(fields.get("depends_on", "[]")),
            description=fields.get("description", ""),
            tools=_parse_list_field(fields.get("tools", "[]")),
            gate=fields.get("gate") if fields.get("gate", "none") != "none" else None,
            gate_policy=fields.get("gate_policy", fields.get("gate", "none")),
            node_type=fields.get("node_type", "engine"),
            model=fields.get("model"),
            max_tokens=int(fields["max_tokens"]) if "max_tokens" in fields else None,
            temperature=float(fields["temperature"]) if "temperature" in fields else None,
        )
        steps.append(step)

    return steps


def _slugify_step_name(name: str) -> str:
    """Convert step display name to a slug: 'Fetch and Categorize' → 'fetch-and-categorize'."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _parse_list_field(value: str) -> list[str]:
    """Parse a YAML-style list field: '[a, b, c]' → ['a', 'b', 'c']."""
    value = value.strip()
    if not value or value == "[]":
        return []
    # Remove brackets
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    # Split on comma, strip whitespace
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


def _parse_optional_str(value: str) -> Optional[str]:
    """Return None for 'none'/'null'/empty, otherwise the string."""
    if not value or value.lower() in ("none", "null", ""):
        return None
    return value
