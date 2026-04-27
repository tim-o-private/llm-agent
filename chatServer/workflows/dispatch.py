"""dispatch_workflow — tool executor for starting workflows.

Called by the ConversationHandler when the agent invokes the
dispatch_workflow tool. Creates a WorkflowRunManager on demand
and delegates to start_run().
"""

import logging
from typing import Any

from .models import MissingParameterError, TemplateNotFoundError
from .registry import get_template_registry
from .run_manager import WorkflowRunManager

logger = logging.getLogger(__name__)


async def dispatch_workflow(
    args: dict,
    user_id: str,
    db_client: Any,
    llm_client: Any,
    tool_schemas: list[dict],
    tool_executors: dict,
    service_registry: dict | None = None,
) -> str:
    """Execute the dispatch_workflow tool.

    Args:
        args: Tool arguments with workflow_name and optional parameters.
        user_id: The user who invoked the tool.
        db_client: Supabase client for workflow_runs table.
        llm_client: LLM client for engine (Anthropic or OpenAI).
        tool_schemas: Available tool schemas for the engine.
        tool_executors: Available tool executors for the engine.
        service_registry: Optional custom service registry for workflow nodes.

    Returns:
        Status message string.
    """
    workflow_name = args.get("workflow_name", "")
    parameters = args.get("parameters", {})

    if not workflow_name:
        return "Error: workflow_name is required."

    from .services import DEFAULT_SERVICE_REGISTRY

    manager = WorkflowRunManager(
        db_client=db_client,
        llm_client=llm_client,
        tool_schemas=tool_schemas,
        tool_executors=tool_executors,
        service_registry=service_registry or DEFAULT_SERVICE_REGISTRY,
    )

    try:
        run_id = await manager.start_run(
            user_id=user_id,
            template_name=workflow_name,
            parameters=parameters,
        )
        return (
            f"Started workflow '{workflow_name}' (run_id: {run_id}). "
            f"I'll keep you updated on progress."
        )
    except TemplateNotFoundError:
        try:
            registry = get_template_registry()
            available = await registry.list_templates(user_id)
            return (
                f"Unknown workflow '{workflow_name}'. "
                f"Available workflows: {', '.join(available) if available else 'none'}."
            )
        except Exception:
            return f"Unknown workflow '{workflow_name}'."
    except MissingParameterError as e:
        return (
            f"Missing required parameters for '{workflow_name}': "
            f"{', '.join(e.missing_params)}"
        )
    except Exception as e:
        logger.error(
            "dispatch_workflow failed: %s", e, exc_info=True
        )
        return f"Failed to start workflow: {e}"
