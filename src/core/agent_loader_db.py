# @docs memory-bank/patterns/agent-patterns.md#pattern-2-database-driven-tool-loading
# @rules memory-bank/rules/agent-rules.json#agent-002
# @examples memory-bank/patterns/agent-patterns.md#pattern-10-tool-registration-system
import json
import logging
import os
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, create_model

from chatServer.database.connection import get_db_connection
from chatServer.tools.gmail_tools import GetGmailTool, SearchGmailTool
from chatServer.tools.memory_tools import (
    CreateMemoriesTool,
    DeleteMemoriesTool,
    GetContextTool,
    GetEntitiesTool,
    GetMemoriesTool,
    LinkMemoriesTool,
    SearchEntitiesTool,
    SearchMemoriesTool,
    SetProjectTool,
    UpdateMemoriesTool,
)
from chatServer.tools.reminder_tools import CreateRemindersTool, DeleteRemindersTool, GetRemindersTool
from chatServer.tools.schedule_tools import CreateSchedulesTool, DeleteSchedulesTool, GetSchedulesTool
from chatServer.tools.task_tools import CreateTasksTool, DeleteTasksTool, GetTasksTool, UpdateTasksTool
from chatServer.tools.update_instructions_tool import UpdateInstructionsTool
from core.agents.customizable_agent import CustomizableAgentExecutor
from core.tools.crud_tool import CRUDTool, CRUDToolInput
from supabase import Client as SupabaseClient
from supabase import create_client
from utils.logging_utils import get_logger

logger = get_logger(__name__)

# Tool registry: maps tools.type column value → Python class.
# The canonical migration (SPEC-019) sets correct type values; legacy aliases
# kept only for safety during migration rollback.
TOOL_REGISTRY: Dict[str, Type] = {
    "CRUDTool": CRUDTool,
    # Gmail
    "SearchGmailTool": SearchGmailTool,
    "GetGmailTool": GetGmailTool,
    "GmailTool": None,  # Special handling — uses config.tool_class
    # Memory
    "CreateMemoriesTool": CreateMemoriesTool,
    "SearchMemoriesTool": SearchMemoriesTool,
    "GetMemoriesTool": GetMemoriesTool,
    "DeleteMemoriesTool": DeleteMemoriesTool,
    "UpdateMemoriesTool": UpdateMemoriesTool,
    "SetProjectTool": SetProjectTool,
    "LinkMemoriesTool": LinkMemoriesTool,
    "GetEntitiesTool": GetEntitiesTool,
    "SearchEntitiesTool": SearchEntitiesTool,
    "GetContextTool": GetContextTool,
    # Tasks
    "GetTasksTool": GetTasksTool,
    "CreateTasksTool": CreateTasksTool,
    "UpdateTasksTool": UpdateTasksTool,
    "DeleteTasksTool": DeleteTasksTool,
    # Reminders
    "GetRemindersTool": GetRemindersTool,
    "CreateRemindersTool": CreateRemindersTool,
    "DeleteRemindersTool": DeleteRemindersTool,
    # Schedules
    "GetSchedulesTool": GetSchedulesTool,
    "CreateSchedulesTool": CreateSchedulesTool,
    "DeleteSchedulesTool": DeleteSchedulesTool,
    # Instructions
    "UpdateInstructionsTool": UpdateInstructionsTool,
}

# Gmail tool class registry for GmailTool type (config.tool_class → class)
GMAIL_TOOL_CLASSES: Dict[str, Type] = {
    "SearchGmailTool": SearchGmailTool,
    "GetGmailTool": GetGmailTool,
}

# Agent registry: maps agent_name to specialized agent classes
# This allows routing specific agents to their specialized implementations
AGENT_REGISTRY: Dict[str, Type] = {}

def register_specialized_agent(agent_name: str, agent_class: Type):
    """Register a specialized agent class for a specific agent name.

    Args:
        agent_name: Name of the agent (e.g., 'email_digest_agent')
        agent_class: Specialized agent class to use
    """
    AGENT_REGISTRY[agent_name] = agent_class
    logger.info(f"Registered specialized agent '{agent_name}' -> {agent_class.__name__}")

def create_specialized_agent(agent_name: str, user_id: str, session_id: str) -> Any:
    """Create a specialized agent instance if one is registered.

    Args:
        agent_name: Name of the agent
        user_id: User ID
        session_id: Session ID

    Returns:
        Specialized agent instance or None if not registered
    """
    if agent_name in AGENT_REGISTRY:
        agent_class = AGENT_REGISTRY[agent_name]
        logger.info(f"Creating specialized agent '{agent_name}' using {agent_class.__name__}")
        return agent_class(user_id=user_id, session_id=session_id)
    return None

def _create_dynamic_crud_tool_class(
    tool_name_from_db: str,
    base_tool_class: Type[CRUDTool],
    runtime_schema_config: Dict[str, Any]
) -> Type[CRUDTool]:
    """
    Dynamically creates a new Python class that inherits from `base_tool_class` (typically CRUDTool)
    and sets a custom `args_schema` class variable on it.

    This custom `args_schema` is a Pydantic model generated from `runtime_schema_config`,
    which defines the expected structure (fields, types, optionality, nested properties)
    for the tool's runtime arguments ('data' and 'filters').

    Args:
        tool_name_from_db: The 'name' of the tool instance from the database, used for
                           generating unique names for the dynamic class and its args model.
        base_tool_class: The parent class to inherit from (e.g., CRUDTool).
        runtime_schema_config: A dictionary defining the structure for the `args_schema`.
                               Example: {
                                   "data": {
                                       "type": "dict", "optional": False, "description": "...",
                                       "properties": { "field1": { "type": "str", ... } }
                                   },
                                   "filters": { ... }
                               }

    Returns:
        A new, dynamically created class type (not an instance) that is a subclass of
        `base_tool_class` with a custom `args_schema`.
        Returns `base_tool_class` itself if `runtime_schema_config` is empty or invalid.
    """
    fields_for_args_model: Dict[str, Any] = {}

    for field_name, field_config in runtime_schema_config.items():
        if not isinstance(field_config, dict):
            logger.warning(f"Dynamic schema for tool '{tool_name_from_db}': Field config for '{field_name}' is not a dict. Skipping.")  # noqa: E501
            continue

        description = field_config.get("description", f"Argument '{field_name}' for tool '{tool_name_from_db}'.")
        is_optional = field_config.get("optional", True)
        field_type_str = field_config.get("type", "any").lower()

        actual_field_type: Type = Any
        if field_type_str == "dict":
            nested_properties = field_config.get("properties")
            if isinstance(nested_properties, dict) and nested_properties:
                nested_model_name = f"{tool_name_from_db.capitalize().replace('_','')}{field_name.capitalize()}PropsModel"  # noqa: E501
                NestedModel = _create_dynamic_args_model(nested_model_name, nested_properties)
                actual_field_type = NestedModel
            else:
                actual_field_type = Dict[str, Any]
        elif field_type_str == "str": actual_field_type = str  # noqa: E701
        elif field_type_str == "int": actual_field_type = int  # noqa: E701
        elif field_type_str == "bool": actual_field_type = bool  # noqa: E701
        elif field_type_str == "list": actual_field_type = List[Any]  # noqa: E701
        # Add more type mappings (e.g., float, enums from strings) as needed.

        if is_optional:
            pydantic_field_definition = (Optional[actual_field_type], Field(default=None, description=description))
        else:
            pydantic_field_definition = (actual_field_type, Field(..., description=description))

        fields_for_args_model[field_name] = pydantic_field_definition

    if not fields_for_args_model:
        logger.warning(f"Dynamic schema for tool '{tool_name_from_db}': No valid fields parsed from runtime_args_schema. Will use default args_schema from base class '{base_tool_class.__name__}'.")  # noqa: E501
        return base_tool_class

    args_model_name = f"{tool_name_from_db.capitalize().replace('_', '')}ArgsSchemaModel"
    SpecificArgsModel = create_model(
        args_model_name,
        **fields_for_args_model,
        __config__=ConfigDict(extra='ignore', arbitrary_types_allowed=True), # Allow arbitrary types for nested models
        __module__=__name__
    )

    dynamic_tool_class_name = f"Dynamic{tool_name_from_db.capitalize().replace('_', '')}{base_tool_class.__name__}"

    class_dict = {
        'args_schema': SpecificArgsModel,
        '__module__': __name__
    }

    DynamicToolClass = type(
        dynamic_tool_class_name,
        (base_tool_class,),
        class_dict
    )
    logger.info(f"Created dynamic tool class '{DynamicToolClass.__name__}' with args_schema '{SpecificArgsModel.__name__}' for tool instance '{tool_name_from_db}'.")  # noqa: E501
    return DynamicToolClass

def _create_dynamic_args_model(model_name: str, properties_config: Dict[str, Any]) -> Type[BaseModel]:
    """
    Helper function to create a Pydantic BaseModel from a dictionary defining its properties.
    Used for creating models for nested structures within a tool's `runtime_args_schema`.

    Args:
        model_name: The desired name for the dynamically created Pydantic model class.
        properties_config: A dictionary where keys are field names and values are dicts
                           configuring each field (e.g., {"type": "str", "optional": False, ...}).

    Returns:
        A new, dynamically created Pydantic BaseModel class type.
        Returns a simple BaseModel subclass with no fields if `properties_config` is empty or invalid.
    """
    fields: Dict[str, Any] = {}
    for prop_name, prop_config in properties_config.items():
        if not isinstance(prop_config, dict):
            logger.warning(f"Dynamic nested model '{model_name}': Property config for '{prop_name}' is not a dict. Skipping.")  # noqa: E501
            continue

        description = prop_config.get("description", f"Property '{prop_name}' of {model_name}.")
        is_optional = prop_config.get("optional", True)
        prop_type_str = prop_config.get("type", "any").lower()

        actual_prop_type: Type = Any
        if prop_type_str == "str": actual_prop_type = str  # noqa: E701
        elif prop_type_str == "int": actual_prop_type = int  # noqa: E701
        elif prop_type_str == "bool": actual_prop_type = bool  # noqa: E701
        elif prop_type_str == "dict": actual_prop_type = Dict[str, Any]  # noqa: E701
        elif prop_type_str == "list": actual_prop_type = List[Any]  # noqa: E701
        # Add more type mappings as needed.

        if is_optional:
            fields[prop_name] = (Optional[actual_prop_type], Field(default=None, description=description))
        else:
            fields[prop_name] = (actual_prop_type, Field(..., description=description))

    if not fields:
        logger.warning(f"Dynamic nested model '{model_name}': No valid properties found in config. Creating a fallback model with no fields.")  # noqa: E501
        # Create a fallback model that can be instantiated but has no specific fields, rather than erroring.
        class EmptyNestedModel(BaseModel):
            model_config = ConfigDict(extra='allow') # Allow extra fields if agent sends them unexpectedly
            pass
        EmptyNestedModel.__name__ = model_name # Assign name for clarity in logs
        return EmptyNestedModel

    return create_model(
        model_name,
        **fields,
        __config__=ConfigDict(extra='ignore', arbitrary_types_allowed=True),
        __module__=__name__
    )

def load_tools_from_db(
    tools_data: List[dict], # List of tool rows from the 'agent_tools' table
    user_id: str,
    agent_name: str,
    supabase_url: str,
    supabase_key: str,
    memory_client=None,
) -> List[Any]: # Returns a list of instantiated tool objects
    """
    Instantiates tool classes based on configuration data fetched from the database.

    For each tool defined in `tools_data`:
    1. Looks up the base Python tool class in `TOOL_REGISTRY` using `tool_row["type"]`.
    2. If the base class is `CRUDTool` and a `runtime_args_schema` is provided in the
       tool's DB `config` (JSONB column), it dynamically creates a subclass of `CRUDTool`
       with a custom `args_schema` generated from this runtime schema. This allows each
       CRUDTool instance to have tailored input validation for the LLM.
    3. Prepares constructor arguments including shared context (`user_id`, `agent_name`, Supabase details)
       and tool-specific parameters sourced from the DB `config` (e.g., `table_name`, `method` for CRUDTool).
    4. Instantiates the (potentially dynamic) tool class with these arguments.

    Args:
        tools_data: A list of dictionaries, where each dict represents a row from the
                    'agent_tools' database table (or a compatible structure).
        user_id: The ID of the current user, passed to tools for data scoping.
        agent_name: The name of the agent invoking the tools, passed for context/scoping.
        supabase_url: The Supabase project URL.
        supabase_key: The Supabase service key.

    Returns:
        A list of instantiated tool objects ready to be used by an agent executor.
    """
    tools: List[Any] = []
    for tool_row in tools_data:
        db_tool_type_str = str(tool_row["type"]) # 'type' column from agent_tools table
        db_tool_config_json = tool_row.get("config") or {} # JSONB 'config' column from agent_tools

        db_tool_name = tool_row.get("name") # 'name' column (for Langchain tool name)
        db_tool_description = tool_row.get("description") # 'description' column (for LLM)

        if not db_tool_name:
            logger.error(f"DB entry for tool type '{db_tool_type_str}' is missing 'name'. Skipping. Row: {tool_row}")
            continue
        if not db_tool_description:
            logger.error(f"DB entry for tool '{db_tool_name}' (type '{db_tool_type_str}') is missing 'description'. Skipping. Row: {tool_row}")  # noqa: E501
            continue

        # Convert to strings after validation
        db_tool_name = str(db_tool_name)
        db_tool_description = str(db_tool_description)

        original_python_tool_class = TOOL_REGISTRY.get(db_tool_type_str)
        if db_tool_type_str not in TOOL_REGISTRY:
            logger.warning(f"Tool type '{db_tool_type_str}' (for tool name '{db_tool_name}') not found in TOOL_REGISTRY. Skipping tool.")  # noqa: E501
            continue

        # Special handling for GmailTool type - use tool_class config to determine specific class
        if db_tool_type_str == "GmailTool":
            tool_class_name = db_tool_config_json.get("tool_class")
            if not tool_class_name:
                logger.error(f"GmailTool instance '{db_tool_name}' is missing 'tool_class' in its DB config. Skipping.")
                continue

            specific_gmail_tool_class = GMAIL_TOOL_CLASSES.get(tool_class_name)
            if not specific_gmail_tool_class:
                logger.error(f"GmailTool instance '{db_tool_name}' has unknown tool_class '{tool_class_name}'. Available: {list(GMAIL_TOOL_CLASSES.keys())}. Skipping.")  # noqa: E501
                continue

            original_python_tool_class = specific_gmail_tool_class
            logger.info(f"GmailTool '{db_tool_name}' resolved to specific class '{tool_class_name}'")

        # This will be the class to instantiate, potentially a dynamic subclass of original_python_tool_class
        effective_tool_class_to_instantiate = original_python_tool_class

        # Prepare common constructor arguments for all tools
        # These include context injected by the loader and BaseTool parameters like name/description.
        # Specific tool classes (like CRUDTool) also define these as Pydantic fields.
        tool_constructor_kwargs = {
            "user_id": user_id,
            "agent_name": agent_name,
            "supabase_url": supabase_url,
            "supabase_key": supabase_key,
            "name": db_tool_name,
            "description": db_tool_description,
        }

        if original_python_tool_class == CRUDTool:
            # Extract CRUDTool-specific operational parameters from its JSONB config
            crud_table_name = db_tool_config_json.get("table_name")
            crud_method = db_tool_config_json.get("method")
            crud_field_map = db_tool_config_json.get("field_map", {}) # Default to empty if not present

            if not crud_table_name:
                logger.error(f"CRUDTool instance '{db_tool_name}' is missing 'table_name' in its DB config. Skipping.")
                continue
            if not crud_method:
                logger.error(f"CRUDTool instance '{db_tool_name}' is missing 'method' in its DB config. Skipping.")
                continue

            # Add CRUDTool specific operational fields to its constructor args
            tool_constructor_kwargs["table_name"] = crud_table_name
            tool_constructor_kwargs["method"] = crud_method
            tool_constructor_kwargs["field_map"] = crud_field_map
            # Example for future config-driven agent_name filtering for CRUDTool:
            # tool_constructor_kwargs["apply_agent_name_filter"] = db_tool_config_json.get("apply_agent_name_filter", False)  # noqa: E501

            raw_runtime_schema_from_db = db_tool_config_json.get("runtime_args_schema")
            parsed_runtime_schema_dict: Optional[Dict[str, Any]] = None
            if isinstance(raw_runtime_schema_from_db, str):
                try:
                    parsed_runtime_schema_dict = json.loads(raw_runtime_schema_from_db)
                except json.JSONDecodeError:
                    logger.error(f"CRUDTool instance '{db_tool_name}': 'runtime_args_schema' in DB config is malformed JSON. Will use default args_schema.")  # noqa: E501
            elif isinstance(raw_runtime_schema_from_db, dict):
                parsed_runtime_schema_dict = raw_runtime_schema_from_db

            if parsed_runtime_schema_dict: # If a valid schema dict was parsed or provided
                try:
                    effective_tool_class_to_instantiate = _create_dynamic_crud_tool_class(
                        db_tool_name,
                        CRUDTool, # Base class for dynamic subclassing
                        parsed_runtime_schema_dict
                    )
                except Exception as e:
                    logger.error(f"CRUDTool instance '{db_tool_name}': Failed to create dynamic class from runtime_args_schema. Error: {e}. Will use default '{CRUDTool.__name__}' args_schema.", exc_info=True)  # noqa: E501
            else:
                logger.info(f"CRUDTool instance '{db_tool_name}': No 'runtime_args_schema' found or parsed in DB config. Will use default '{CRUDTool.__name__}' args_schema ('{CRUDToolInput.__name__}').")  # noqa: E501

        else: # For non-CRUD tools registered in TOOL_REGISTRY
            # Merge their entire DB config JSON into constructor args.
            # These tools must handle these kwargs in their __init__ or have them as Pydantic fields.
            if db_tool_config_json:
                logger.info(f"For non-CRUD tool '{db_tool_name}' (type '{db_tool_type_str}'), merging its DB config keys ({list(db_tool_config_json.keys())}) into constructor arguments.")  # noqa: E501
                tool_constructor_kwargs.update(db_tool_config_json)

            # Inject memory_client for memory tools; strip Supabase kwargs they don't need
            _memory_tool_types = (
                "CreateMemoriesTool", "SearchMemoriesTool", "GetMemoriesTool",
                "DeleteMemoriesTool", "UpdateMemoriesTool",
                "SetProjectTool", "LinkMemoriesTool", "GetEntitiesTool",
                "SearchEntitiesTool", "GetContextTool",
                # Legacy DB type strings
                "StoreMemoryTool", "RecallMemoryTool", "SearchMemoryTool",
                "FetchMemoryTool", "DeleteMemoryTool", "UpdateMemoryTool",
                "ListEntitiesTool", "GetContextInfoTool",
            )
            if db_tool_type_str in _memory_tool_types:
                if memory_client:
                    tool_constructor_kwargs["memory_client"] = memory_client
                tool_constructor_kwargs.pop("supabase_url", None)
                tool_constructor_kwargs.pop("supabase_key", None)

        logger.debug(f"Attempting to instantiate tool '{db_tool_name}' (effective class '{effective_tool_class_to_instantiate.__name__}') with kwargs: {list(tool_constructor_kwargs.keys())}")  # noqa: E501

        try:
            tool_instance = effective_tool_class_to_instantiate(**tool_constructor_kwargs)
            tools.append(tool_instance)

            # Sanity check for Langchain compatibility after instantiation
            if not getattr(tool_instance, 'name', None) or not getattr(tool_instance, 'description', None):
                 logger.warning(f"Instantiated tool '{db_tool_name}' appears to be missing standard 'name' or 'description' attributes post-init. This might cause issues with Langchain.")  # noqa: E501

            if isinstance(tool_instance, CRUDTool):
                effective_args_schema_name = type(tool_instance.args_schema).__name__ if tool_instance.args_schema else "None"  # noqa: E501
                if effective_args_schema_name != CRUDToolInput.__name__ and tool_instance.args_schema is not CRUDToolInput:  # noqa: E501
                    logger.info(f"CRUDTool instance '{tool_instance.name}' was instantiated with a dynamic args_schema: '{effective_args_schema_name}'.")  # noqa: E501
                else:
                    logger.info(f"CRUDTool instance '{tool_instance.name}' was instantiated with the default args_schema: '{CRUDToolInput.__name__}'.")  # noqa: E501

            logger.info(f"Successfully instantiated tool: '{getattr(tool_instance, 'name', db_tool_name)}' (Python class '{type(tool_instance).__name__}')")  # noqa: E501
        except Exception as e:
            logger.error(f"Failed to instantiate tool class '{db_tool_type_str}' (intended name '{db_tool_name}', effective Python class '{effective_tool_class_to_instantiate.__name__}'): {e}", exc_info=True)  # noqa: E501
    return tools

def _fetch_user_instructions(db: SupabaseClient, user_id: str, agent_name: str) -> Optional[str]:
    """Fetch user instructions from user_agent_prompt_customizations.

    Returns the instructions TEXT or None if no row exists.
    """
    try:
        resp = (
            db.table("user_agent_prompt_customizations")
            .select("instructions")
            .eq("user_id", user_id)
            .eq("agent_name", agent_name)
            .maybe_single()
            .execute()
        )
        if resp.data:
            return resp.data.get("instructions") or None
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch user instructions for {user_id}/{agent_name}: {e}")
        return None


async def _resolve_memory_user_id(user_id: str) -> str:
    """Resolve Supabase user ID to min-memory user identity.

    Reads auth.users.raw_user_meta_data->>'provider_id' and formats as
    'google-oauth2|{provider_id}'. Falls back to Supabase UUID.
    """
    try:
        async for conn in get_db_connection():
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT raw_user_meta_data->>'provider_id' FROM auth.users WHERE id = %s",
                    (user_id,),
                )
                row = await cur.fetchone()
                if row and row[0]:
                    return f"google-oauth2|{row[0]}"
        return user_id
    except Exception as e:
        logger.warning("Failed to resolve memory user ID for %s: %s", user_id, e)
        return user_id


async def _prefetch_memory_notes(memory_client) -> Optional[str]:
    """Pre-fetch top memories from min-memory for the 'What You Know' prompt section."""
    if not memory_client or not memory_client.base_url:
        return None
    try:
        result = await memory_client.call_tool("retrieve_context", {
            "query": "user context and preferences",
            "memory_type": ["core_identity", "project_context"],
            "limit": 10,
        })
        # Response is direct JSON from /api/tools/call
        memories = result if isinstance(result, list) else result.get("memories", result.get("results", []))
        if not memories:
            return None
        lines = []
        for mem in memories:
            if isinstance(mem, dict) and "text" in mem:
                lines.append(f"- {mem['text']}")
        return "\n".join(lines) if lines else None
    except Exception as e:
        logger.warning("Failed to pre-fetch memory notes: %s", e)
        return None


def load_agent_executor_db(
    agent_name: str,
    user_id: str,
    session_id: str,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    log_level: int = logging.INFO,
    channel: str = "web",
    use_cache: bool = True,  # Default to using cache for better performance
    last_message_at=None,
) -> CustomizableAgentExecutor:
    """
    Loads an agent's configuration and its associated tools from the database,
    instantiates the tools (dynamically configuring CRUDTools with custom argument schemas
    if specified), and returns an initialized `CustomizableAgentExecutor`.

    Workflow:
    1. Fetches the agent's core configuration (LLM settings, system prompt) from 'agent_configurations'.
    2. Fetches the list of active tools assigned to this agent from 'agent_tools' joined with 'tools',
       including their type, name, description, and JSONB configuration.
    3. Calls `load_tools_from_db` to instantiate these tools, which handles dynamic
       `args_schema` creation for CRUDTools based on `runtime_args_schema` in their config.
    4. Initializes and returns a `CustomizableAgentExecutor` with the loaded agent config and tools.

    Args:
        agent_name: The name of the agent to load (must match 'agent_name' in DB).
        user_id: The ID of the current user, for data scoping and context.
        session_id: The active session ID, for short-term memory and context.
        supabase_url: Supabase project URL. Defaults to SUPABASE_URL env var.
        supabase_key: Supabase service key. Defaults to SUPABASE_SERVICE_ROLE_KEY env var.
        log_level: Desired logging level for the logger instance used by the executor.
        use_cache: Whether to use the tool cache service for improved performance. Defaults to True.

    Returns:
        An initialized `CustomizableAgentExecutor` instance.

    Raises:
        ValueError: If Supabase URL/key are missing or agent not found in DB.
        Various exceptions from tool instantiation or executor creation if errors occur.
    """
    logger.setLevel(log_level)

    effective_supabase_url = supabase_url or os.getenv("SUPABASE_URL")
    effective_supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not effective_supabase_url or not effective_supabase_key:
        raise ValueError("Supabase URL and Service Key must be provided either as arguments or environment variables (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY).")  # noqa: E501

    db: SupabaseClient = create_client(effective_supabase_url, effective_supabase_key)

    # Create memory client from env vars
    import asyncio as _asyncio

    mem_url = os.getenv("MEMORY_SERVER_URL", "")
    mem_key = os.getenv("MEMORY_SERVER_BACKEND_KEY", "")
    memory_client = None
    if mem_url and mem_key:
        from chatServer.services.memory_client import MemoryClient

        memory_user_id = _asyncio.run(_resolve_memory_user_id(user_id))
        memory_client = MemoryClient(base_url=mem_url, backend_key=mem_key, user_id=memory_user_id)

    cache_status = "cached" if use_cache else "non-cached"
    logger.info(f"Loading agent executor for agent_name='{agent_name}', user_id='{user_id}' using {cache_status} database-driven agent loading.")  # noqa: E501

    # 1. Fetch agent config (not cached as it's infrequent and small)
    agent_resp = db.table("agent_configurations").select("*, id").eq("agent_name", agent_name).single().execute()
    if not agent_resp.data:
        raise ValueError(f"Agent configuration for '{agent_name}' not found in 'agent_configurations' table.")

    agent_db_config = agent_resp.data
    agent_id = agent_db_config.get("id")
    if not agent_id:
        raise ValueError(f"Agent '{agent_name}' found, but its ID (UUID from agent_configurations table) is missing. This is unexpected.")  # noqa: E501
    logger.info(f"Loaded agent config for '{agent_name}' (ID: {agent_id}) from DB.")

    # 2. Fetch tools - use cache if requested and available
    tools_data_from_db = []

    if use_cache:
        try:
            # Try to use cache service
            import asyncio

            from chatServer.services.tool_cache_service import get_cached_tools_for_agent

            cached_tools_data = asyncio.run(get_cached_tools_for_agent(str(agent_id)))
            logger.info(f"Retrieved {len(cached_tools_data)} tools for agent '{agent_name}' from cache")

            # Transform cached tool data to match expected format
            for tool_config in cached_tools_data:
                transformed_tool = {
                    "name": tool_config["name"],
                    "type": tool_config.get("type", "CRUDTool"),
                    "description": tool_config.get("description", ""),
                    "config": tool_config.get("config", {}),
                    "is_active": tool_config.get("is_active", True)
                }
                tools_data_from_db.append(transformed_tool)

        except ImportError:
            logger.warning("Tool cache service not available, falling back to direct database query")
            use_cache = False
        except Exception as e:
            logger.error(f"Failed to get tools from cache for agent '{agent_name}': {e}")
            logger.info("Falling back to direct database query")
            use_cache = False

    if not use_cache:
        # Fallback to direct database query using normalized schema
        async def get_agent_tools():
            async for conn in get_db_connection():
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT
                            at.id as assignment_id,
                            at.config_override,
                            at.is_active as assignment_active,
                            t.id as tool_id,
                            t.name,
                            t.type,
                            t.description,
                            t.config,
                            t.is_active as tool_active
                        FROM agent_tools at
                        JOIN tools t ON at.tool_id = t.id
                        WHERE at.agent_id = %s
                        AND at.is_active = true
                        AND at.is_deleted = false
                        AND t.is_active = true
                        AND t.is_deleted = false
                    """, (str(agent_id),))

                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]

        # Since this is a sync function, we need to run the async query
        import asyncio
        try:
            raw_tools_data = asyncio.run(get_agent_tools())
        except Exception as e:
            logger.error(f"Failed to fetch tools using connection pool: {e}")
            # Fallback to Supabase client with separate queries
            logger.info("Falling back to Supabase client with separate queries")

            # First get agent tool assignments
            assignments_resp = db.table("agent_tools").select("*").eq("agent_id", str(agent_id)).eq("is_active", True).eq("is_deleted", False).execute()  # noqa: E501
            assignments = assignments_resp.data or []

            # Then get tool details for each assignment
            raw_tools_data = []
            for assignment in assignments:
                tool_resp = db.table("tools").select("*").eq("id", assignment["tool_id"]).eq("is_active", True).eq("is_deleted", False).single().execute()  # noqa: E501
                if tool_resp.data:
                    tool_data = tool_resp.data
                    # Merge assignment and tool data
                    merged_data = {
                        "assignment_id": assignment["id"],
                        "config_override": assignment.get("config_override", {}),
                        "assignment_active": assignment["is_active"],
                        "tool_id": tool_data["id"],
                        "name": tool_data["name"],
                        "type": tool_data["type"],
                        "description": tool_data.get("description", ""),
                        "config": tool_data.get("config", {}),
                        "tool_active": tool_data["is_active"]
                    }
                    raw_tools_data.append(merged_data)

        logger.info(f"Found {len(raw_tools_data)} active tools linked to agent '{agent_name}' (agent_id: {agent_id}) via normalized schema.")  # noqa: E501

        # Transform the joined data to match the expected format for load_tools_from_db
        # Merge tool config with config_override from agent_tools
        for tool_data in raw_tools_data:
            # Start with the base tool config
            merged_config = tool_data.get("config", {})

            # Apply agent-specific config overrides
            config_override = tool_data.get("config_override", {})
            if config_override:
                if isinstance(merged_config, dict) and isinstance(config_override, dict):
                    merged_config.update(config_override)
                else:
                    # If either is not a dict, use override as the config
                    merged_config = config_override

            # Create the expected tool data structure
            transformed_tool = {
                "id": tool_data["assignment_id"],  # Use assignment ID for uniqueness
                "name": tool_data["name"],
                "type": tool_data["type"],
                "description": tool_data.get("description", ""),
                "config": merged_config,
                "is_active": tool_data["assignment_active"]
            }
            tools_data_from_db.append(transformed_tool)

    # 3. Instantiate tools using the helper function
    instantiated_tools = load_tools_from_db(
        tools_data=tools_data_from_db,
        user_id=user_id,
        agent_name=agent_db_config["agent_name"],
        supabase_url=effective_supabase_url,
        supabase_key=effective_supabase_key,
        memory_client=memory_client,
    )

    # 4. Prepare LLM config and assemble system prompt via prompt builder
    llm_config_from_db = agent_db_config.get("llm_config")

    if not llm_config_from_db:
        logger.warning(f"Agent '{agent_name}' is missing 'llm_config' in its DB configuration. LLM behavior might be undefined.")  # noqa: E501

    # Fetch soul (was system_prompt) and identity from agent config
    soul = agent_db_config.get("soul") or ""
    identity = agent_db_config.get("identity")

    # Fetch user instructions from user_agent_prompt_customizations
    user_instructions = _fetch_user_instructions(db, user_id, agent_name)

    # Fetch memory notes from min-memory for prompt
    memory_notes = _asyncio.run(_prefetch_memory_notes(memory_client))

    # Assemble the system prompt via the prompt builder
    from chatServer.services.prompt_builder import build_agent_prompt
    assembled_prompt = build_agent_prompt(
        soul=soul,
        identity=identity,
        channel=channel,
        user_instructions=user_instructions,
        tools=instantiated_tools,
        memory_notes=memory_notes,
        last_message_at=last_message_at,
    )

    agent_config_for_executor = {
        "agent_name": agent_db_config["agent_name"],
        "llm": llm_config_from_db or {},
        "system_prompt": assembled_prompt,
    }

    # 5. Create and return the executor
    try:
        agent_executor = CustomizableAgentExecutor.from_agent_config(
            agent_config_dict=agent_config_for_executor,
            tools=instantiated_tools,
            user_id=user_id,
            session_id=session_id,
            logger_instance=logger
        )
        logger.info(f"Successfully created CustomizableAgentExecutor for agent '{agent_db_config['agent_name']}' using {cache_status} DB data.")  # noqa: E501
        return agent_executor
    except Exception as e:
        logger.error(f"Failed to create CustomizableAgentExecutor for agent '{agent_db_config['agent_name']}': {e}", exc_info=True)  # noqa: E501
        raise


async def load_agent_executor_db_async(
    agent_name: str,
    user_id: str,
    session_id: str,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    log_level: int = logging.INFO,
    channel: str = "web",
    last_message_at=None,
) -> CustomizableAgentExecutor:
    """Async version of load_agent_executor_db.

    Eliminates asyncio.run() calls and event loop blocking.
    Uses cached agent config and user instructions, parallelizes
    tools + user_instructions fetch via asyncio.gather().
    """
    import asyncio

    from chatServer.services.agent_config_cache_service import get_cached_agent_config
    from chatServer.services.tool_cache_service import get_cached_tools_for_agent
    from chatServer.services.user_instructions_cache_service import get_cached_user_instructions

    logger.setLevel(log_level)

    effective_supabase_url = supabase_url or os.getenv("SUPABASE_URL")
    effective_supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not effective_supabase_url or not effective_supabase_key:
        raise ValueError("Supabase URL and Service Key must be provided either as arguments or environment variables.")

    logger.info(f"Loading agent executor (async) for agent_name='{agent_name}', user_id='{user_id}'")

    # Resolve memory user ID and create MemoryClient
    memory_user_id = await _resolve_memory_user_id(user_id)
    memory_client = None
    mem_url = os.getenv("MEMORY_SERVER_URL", "")
    mem_key = os.getenv("MEMORY_SERVER_BACKEND_KEY", "")
    if mem_url and mem_key:
        from chatServer.services.memory_client import MemoryClient

        memory_client = MemoryClient(base_url=mem_url, backend_key=mem_key, user_id=memory_user_id)

    # Step 1: Agent config from cache (~0ms on hit)
    agent_db_config = await get_cached_agent_config(agent_name)
    if not agent_db_config:
        # Cache miss or empty — fall back to direct DB query
        agent_db_config = await _fetch_agent_config_from_db_async(agent_name)

    if not agent_db_config:
        raise ValueError(f"Agent configuration for '{agent_name}' not found in 'agent_configurations' table.")

    agent_id = agent_db_config.get("id")
    if not agent_id:
        raise ValueError(f"Agent '{agent_name}' found, but its ID is missing.")

    logger.info(f"Loaded agent config for '{agent_name}' (ID: {agent_id}) from cache/DB.")

    # Step 2: Parallelize tools + user instructions + memory notes fetch
    tools_task = get_cached_tools_for_agent(str(agent_id))
    instructions_task = get_cached_user_instructions(user_id, agent_name)
    memory_task = _prefetch_memory_notes(memory_client)
    cached_tools_data, user_instructions, memory_notes = await asyncio.gather(
        tools_task, instructions_task, memory_task
    )

    # Transform cached tool data to match expected format
    tools_data_from_db = []
    for tool_config in cached_tools_data:
        transformed_tool = {
            "name": tool_config["name"],
            "type": tool_config.get("type", "CRUDTool"),
            "description": tool_config.get("description", ""),
            "config": tool_config.get("config", {}),
            "is_active": tool_config.get("is_active", True),
        }
        tools_data_from_db.append(transformed_tool)

    logger.info(f"Retrieved {len(tools_data_from_db)} tools for agent '{agent_name}' (async path)")

    # Step 3: Instantiate tools
    instantiated_tools = load_tools_from_db(
        tools_data=tools_data_from_db,
        user_id=user_id,
        agent_name=agent_db_config["agent_name"],
        supabase_url=effective_supabase_url,
        supabase_key=effective_supabase_key,
        memory_client=memory_client,
    )

    # Step 4: Build prompt
    llm_config_from_db = agent_db_config.get("llm_config")
    if not llm_config_from_db:
        logger.warning(f"Agent '{agent_name}' is missing 'llm_config' in its DB configuration.")

    soul = agent_db_config.get("soul") or ""
    identity = agent_db_config.get("identity")

    from chatServer.services.prompt_builder import build_agent_prompt

    assembled_prompt = build_agent_prompt(
        soul=soul,
        identity=identity,
        channel=channel,
        user_instructions=user_instructions,
        tools=instantiated_tools,
        memory_notes=memory_notes,
        last_message_at=last_message_at,
    )

    agent_config_for_executor = {
        "agent_name": agent_db_config["agent_name"],
        "llm": llm_config_from_db or {},
        "system_prompt": assembled_prompt,
    }

    # Step 5: Create and return the executor
    try:
        agent_executor = CustomizableAgentExecutor.from_agent_config(
            agent_config_dict=agent_config_for_executor,
            tools=instantiated_tools,
            user_id=user_id,
            session_id=session_id,
            logger_instance=logger,
        )
        agent_nm = agent_db_config['agent_name']
        logger.info(f"Successfully created CustomizableAgentExecutor (async) for agent '{agent_nm}'.")
        return agent_executor
    except Exception as e:
        agent_nm = agent_db_config['agent_name']
        logger.error(f"Failed to create async executor for agent '{agent_nm}': {e}", exc_info=True)
        raise


async def _fetch_agent_config_from_db_async(agent_name: str) -> Optional[Dict[str, Any]]:
    """Direct DB fetch for agent config when cache misses."""
    try:
        from chatServer.database.connection import get_database_manager

        db_manager = get_database_manager()
        async for conn in db_manager.get_connection():
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id, agent_name, soul, identity, llm_config,
                           created_at, updated_at
                    FROM agent_configurations
                    WHERE agent_name = %s
                """, (agent_name,))
                row = await cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))
        return None
    except Exception as e:
        logger.error(f"Failed to fetch agent config from DB for '{agent_name}': {e}")
        return None


