# @docs memory-bank/patterns/agent-patterns.md#pattern-2-database-driven-tool-loading
# @rules memory-bank/rules/agent-rules.json#agent-002
# @examples memory-bank/patterns/agent-patterns.md#pattern-10-tool-registration-system
import json
import logging
import os
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, create_model

from chatServer.database.connection import get_db_connection
from chatServer.tools.email_digest_tool import EmailDigestTool
from chatServer.tools.gmail_tools import GmailDigestTool, GmailGetMessageTool, GmailSearchTool
from core.agents.customizable_agent import CustomizableAgentExecutor
from core.tools.crud_tool import CRUDTool, CRUDToolInput
from supabase import Client as SupabaseClient
from supabase import create_client

# Example imports for specific tool subclasses (USER ACTION: Add actual tool class imports here)
# from core.tools.agent_memory_tools import CreateMemoryTool, FetchMemoryTool, UpdateMemoryTool, DeleteMemoryTool
from utils.logging_utils import get_logger

logger = get_logger(__name__)

# Tool registry: maps tool_type string from DB to Python class
# Option 2: Registering generic CRUDTool to be configured by DB.
TOOL_REGISTRY: Dict[str, Type] = {
    "CRUDTool": CRUDTool,
    "GmailDigestTool": GmailDigestTool,
    "GmailSearchTool": GmailSearchTool,
    "GmailGetMessageTool": GmailGetMessageTool,
    "EmailDigestTool": EmailDigestTool,
    "GmailTool": None,  # Special handling - uses tool_class config to determine specific class
    # Add other distinct, non-CRUDTool Python classes here if any.
    # The string key (e.g., "CRUDTool") must match the 'type' column
    # (or ENUM value as string) in your agent_tools table for these tools.
}

# Gmail tool class registry for GmailTool type
GMAIL_TOOL_CLASSES: Dict[str, Type] = {
    "GmailDigestTool": GmailDigestTool,
    "GmailSearchTool": GmailSearchTool,
    "GmailGetMessageTool": GmailGetMessageTool,
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
            logger.warning(f"Dynamic schema for tool '{tool_name_from_db}': Field config for '{field_name}' is not a dict. Skipping.")
            continue

        description = field_config.get("description", f"Argument '{field_name}' for tool '{tool_name_from_db}'.")
        is_optional = field_config.get("optional", True)
        field_type_str = field_config.get("type", "any").lower()

        actual_field_type: Type = Any
        if field_type_str == "dict":
            nested_properties = field_config.get("properties")
            if isinstance(nested_properties, dict) and nested_properties:
                nested_model_name = f"{tool_name_from_db.capitalize().replace('_','')}{field_name.capitalize()}PropsModel"
                NestedModel = _create_dynamic_args_model(nested_model_name, nested_properties)
                actual_field_type = NestedModel
            else:
                actual_field_type = Dict[str, Any]
        elif field_type_str == "str": actual_field_type = str
        elif field_type_str == "int": actual_field_type = int
        elif field_type_str == "bool": actual_field_type = bool
        elif field_type_str == "list": actual_field_type = List[Any]
        # Add more type mappings (e.g., float, enums from strings) as needed.

        if is_optional:
            pydantic_field_definition = (Optional[actual_field_type], Field(default=None, description=description))
        else:
            pydantic_field_definition = (actual_field_type, Field(..., description=description))

        fields_for_args_model[field_name] = pydantic_field_definition

    if not fields_for_args_model:
        logger.warning(f"Dynamic schema for tool '{tool_name_from_db}': No valid fields parsed from runtime_args_schema. Will use default args_schema from base class '{base_tool_class.__name__}'.")
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
    logger.info(f"Created dynamic tool class '{DynamicToolClass.__name__}' with args_schema '{SpecificArgsModel.__name__}' for tool instance '{tool_name_from_db}'.")
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
            logger.warning(f"Dynamic nested model '{model_name}': Property config for '{prop_name}' is not a dict. Skipping.")
            continue

        description = prop_config.get("description", f"Property '{prop_name}' of {model_name}.")
        is_optional = prop_config.get("optional", True)
        prop_type_str = prop_config.get("type", "any").lower()

        actual_prop_type: Type = Any
        if prop_type_str == "str": actual_prop_type = str
        elif prop_type_str == "int": actual_prop_type = int
        elif prop_type_str == "bool": actual_prop_type = bool
        elif prop_type_str == "dict": actual_prop_type = Dict[str, Any]
        elif prop_type_str == "list": actual_prop_type = List[Any]
        # Add more type mappings as needed.

        if is_optional:
            fields[prop_name] = (Optional[actual_prop_type], Field(default=None, description=description))
        else:
            fields[prop_name] = (actual_prop_type, Field(..., description=description))

    if not fields:
        logger.warning(f"Dynamic nested model '{model_name}': No valid properties found in config. Creating a fallback model with no fields.")
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
            logger.error(f"DB entry for tool '{db_tool_name}' (type '{db_tool_type_str}') is missing 'description'. Skipping. Row: {tool_row}")
            continue

        # Convert to strings after validation
        db_tool_name = str(db_tool_name)
        db_tool_description = str(db_tool_description)

        original_python_tool_class = TOOL_REGISTRY.get(db_tool_type_str)
        if db_tool_type_str not in TOOL_REGISTRY:
            logger.warning(f"Tool type '{db_tool_type_str}' (for tool name '{db_tool_name}') not found in TOOL_REGISTRY. Skipping tool.")
            continue

        # Special handling for GmailTool type - use tool_class config to determine specific class
        if db_tool_type_str == "GmailTool":
            tool_class_name = db_tool_config_json.get("tool_class")
            if not tool_class_name:
                logger.error(f"GmailTool instance '{db_tool_name}' is missing 'tool_class' in its DB config. Skipping.")
                continue

            specific_gmail_tool_class = GMAIL_TOOL_CLASSES.get(tool_class_name)
            if not specific_gmail_tool_class:
                logger.error(f"GmailTool instance '{db_tool_name}' has unknown tool_class '{tool_class_name}'. Available: {list(GMAIL_TOOL_CLASSES.keys())}. Skipping.")
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
            # tool_constructor_kwargs["apply_agent_name_filter"] = db_tool_config_json.get("apply_agent_name_filter", False)

            raw_runtime_schema_from_db = db_tool_config_json.get("runtime_args_schema")
            parsed_runtime_schema_dict: Optional[Dict[str, Any]] = None
            if isinstance(raw_runtime_schema_from_db, str):
                try:
                    parsed_runtime_schema_dict = json.loads(raw_runtime_schema_from_db)
                except json.JSONDecodeError:
                    logger.error(f"CRUDTool instance '{db_tool_name}': 'runtime_args_schema' in DB config is malformed JSON. Will use default args_schema.")
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
                    logger.error(f"CRUDTool instance '{db_tool_name}': Failed to create dynamic class from runtime_args_schema. Error: {e}. Will use default '{CRUDTool.__name__}' args_schema.", exc_info=True)
            else:
                logger.info(f"CRUDTool instance '{db_tool_name}': No 'runtime_args_schema' found or parsed in DB config. Will use default '{CRUDTool.__name__}' args_schema ('{CRUDToolInput.__name__}').")

        else: # For non-CRUD tools registered in TOOL_REGISTRY
            # Merge their entire DB config JSON into constructor args.
            # These tools must handle these kwargs in their __init__ or have them as Pydantic fields.
            if db_tool_config_json:
                logger.info(f"For non-CRUD tool '{db_tool_name}' (type '{db_tool_type_str}'), merging its DB config keys ({list(db_tool_config_json.keys())}) into constructor arguments.")
                tool_constructor_kwargs.update(db_tool_config_json)

        logger.debug(f"Attempting to instantiate tool '{db_tool_name}' (effective class '{effective_tool_class_to_instantiate.__name__}') with kwargs: {list(tool_constructor_kwargs.keys())}")

        try:
            tool_instance = effective_tool_class_to_instantiate(**tool_constructor_kwargs)
            tools.append(tool_instance)

            # Sanity check for Langchain compatibility after instantiation
            if not getattr(tool_instance, 'name', None) or not getattr(tool_instance, 'description', None):
                 logger.warning(f"Instantiated tool '{db_tool_name}' appears to be missing standard 'name' or 'description' attributes post-init. This might cause issues with Langchain.")

            if isinstance(tool_instance, CRUDTool):
                effective_args_schema_name = type(tool_instance.args_schema).__name__ if tool_instance.args_schema else "None"
                if effective_args_schema_name != CRUDToolInput.__name__ and tool_instance.args_schema is not CRUDToolInput:
                    logger.info(f"CRUDTool instance '{tool_instance.name}' was instantiated with a dynamic args_schema: '{effective_args_schema_name}'.")
                else:
                    logger.info(f"CRUDTool instance '{tool_instance.name}' was instantiated with the default args_schema: '{CRUDToolInput.__name__}'.")

            logger.info(f"Successfully instantiated tool: '{getattr(tool_instance, 'name', db_tool_name)}' (Python class '{type(tool_instance).__name__}')")
        except Exception as e:
            logger.error(f"Failed to instantiate tool class '{db_tool_type_str}' (intended name '{db_tool_name}', effective Python class '{effective_tool_class_to_instantiate.__name__}'): {e}", exc_info=True)
    return tools

def load_agent_executor_db(
    agent_name: str,
    user_id: str,
    session_id: str,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    log_level: int = logging.INFO,
    explicit_custom_instructions: Optional[Dict[str, Any]] = None,
    use_cache: bool = True,  # Default to using cache for better performance
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
        supabase_url: Supabase project URL. Defaults to VITE_SUPABASE_URL env var.
        supabase_key: Supabase service key. Defaults to SUPABASE_SERVICE_KEY env var.
        log_level: Desired logging level for the logger instance used by the executor.
        explicit_custom_instructions: Optional dictionary of custom instructions to override
                                      or supplement any loaded from context or defaults.
        use_cache: Whether to use the tool cache service for improved performance. Defaults to True.

    Returns:
        An initialized `CustomizableAgentExecutor` instance.

    Raises:
        ValueError: If Supabase URL/key are missing or agent not found in DB.
        Various exceptions from tool instantiation or executor creation if errors occur.
    """
    logger.setLevel(log_level)

    effective_supabase_url = supabase_url or os.getenv("VITE_SUPABASE_URL")
    effective_supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")
    if not effective_supabase_url or not effective_supabase_key:
        raise ValueError("Supabase URL and Service Key must be provided either as arguments or environment variables (VITE_SUPABASE_URL, SUPABASE_SERVICE_KEY).")

    db: SupabaseClient = create_client(effective_supabase_url, effective_supabase_key)

    cache_status = "cached" if use_cache else "non-cached"
    logger.info(f"Loading agent executor for agent_name='{agent_name}', user_id='{user_id}' using {cache_status} database-driven agent loading.")

    # 1. Fetch agent config (not cached as it's infrequent and small)
    agent_resp = db.table("agent_configurations").select("*, id").eq("agent_name", agent_name).single().execute()
    if not agent_resp.data:
        raise ValueError(f"Agent configuration for '{agent_name}' not found in 'agent_configurations' table.")

    agent_db_config = agent_resp.data
    agent_id = agent_db_config.get("id")
    if not agent_id:
        raise ValueError(f"Agent '{agent_name}' found, but its ID (UUID from agent_configurations table) is missing. This is unexpected.")
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
            assignments_resp = db.table("agent_tools").select("*").eq("agent_id", str(agent_id)).eq("is_active", True).eq("is_deleted", False).execute()
            assignments = assignments_resp.data or []

            # Then get tool details for each assignment
            raw_tools_data = []
            for assignment in assignments:
                tool_resp = db.table("tools").select("*").eq("id", assignment["tool_id"]).eq("is_active", True).eq("is_deleted", False).single().execute()
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

        logger.info(f"Found {len(raw_tools_data)} active tools linked to agent '{agent_name}' (agent_id: {agent_id}) via normalized schema.")

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
    )

    # 4. Prepare LLM config and system prompt from the agent's DB configuration
    llm_config_from_db = agent_db_config.get("llm_config")
    system_prompt_from_db = agent_db_config.get("system_prompt")

    if not llm_config_from_db:
        logger.warning(f"Agent '{agent_name}' is missing 'llm_config' in its DB configuration. LLM behavior might be undefined.")
    if not system_prompt_from_db:
        logger.warning(f"Agent '{agent_name}' is missing 'system_prompt' in its DB configuration. Using a default or empty prompt.")

    agent_config_for_executor = {
        "agent_name": agent_db_config["agent_name"],
        "llm": llm_config_from_db or {},
        "system_prompt": system_prompt_from_db or "",
    }

    # 5. Create and return the executor
    try:
        agent_executor = CustomizableAgentExecutor.from_agent_config(
            agent_config_dict=agent_config_for_executor,
            tools=instantiated_tools,
            user_id=user_id,
            session_id=session_id,
            ltm_notes_content=None,
            explicit_custom_instructions_dict=explicit_custom_instructions,
            logger_instance=logger
        )
        logger.info(f"Successfully created CustomizableAgentExecutor for agent '{agent_db_config['agent_name']}' using {cache_status} DB data.")
        return agent_executor
    except Exception as e:
        logger.error(f"Failed to create CustomizableAgentExecutor for agent '{agent_db_config['agent_name']}': {e}", exc_info=True)
        raise


async def fetch_ltm_notes(user_id: str, agent_name: str, supabase_client=None) -> Optional[str]:
    """Fetch long-term memory notes for a user+agent from the database.

    Args:
        user_id: The user's ID.
        agent_name: The agent name (matches agent_id column in agent_long_term_memory).
        supabase_client: Optional async Supabase client. If not provided, one will be obtained.

    Returns:
        The LTM notes string, or None if no notes exist.
    """
    try:
        if supabase_client is None:
            from chatServer.database.supabase_client import get_supabase_client
            supabase_client = await get_supabase_client()

        ltm_result = await supabase_client.table("agent_long_term_memory").select("notes").eq(
            "user_id", user_id
        ).eq("agent_id", agent_name).maybe_single().execute()

        if ltm_result.data:
            notes = ltm_result.data.get("notes")
            if notes:
                logger.info(f"Loaded LTM for user={user_id}, agent={agent_name} ({len(notes)} chars)")
                return notes

        logger.debug(f"No LTM found for user={user_id}, agent={agent_name}")
        return None

    except Exception as e:
        logger.warning(f"Failed to load LTM for {user_id}/{agent_name}: {e}")
        return None
