import json
from typing import Optional, Any, Dict, ClassVar, Type
from pydantic import BaseModel, Field, ConfigDict, create_model
from supabase import create_client
from langchain_core.tools import BaseTool, ToolException
from utils.logging_utils import get_logger
# Try to import Pydantic v1 specific tool for creating models from dicts, 
# as a simpler first step than full JSON Schema to Pydantic v2 model.
logger = get_logger(__name__)
try:
    from pydantic.v1.tools import create_model_from_typeddict # For Pydantic v1.x
except ImportError:
    try:
        from pydantic.tools import create_model_from_typeddict # Pydantic v2 might have it in a different spot
    except ImportError:
        create_model_from_typeddict = None # Sentinel if not found
        logger.warning("Failed to import create_model_from_typeddict from pydantic.v1.tools or pydantic.tools. Dynamic schema creation might be limited.")

class CRUDToolInput(BaseModel):
    """
    Default Pydantic model for CRUDTool's arguments if no dynamic schema is provided.
    This serves as a fallback and a basic structure. Specific tool instances configured
    in the database will typically have a dynamically generated `args_schema` based on
    their `runtime_args_schema` configuration.
    """
    data: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Data for 'create' or 'update' operations. The expected structure of this dictionary is defined by the specific tool instance's 'runtime_args_schema' in the database."
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Filters for 'fetch', 'update', or 'delete' operations. The expected structure of this dictionary is defined by the specific tool instance's 'runtime_args_schema' in the database."
    )

class CRUDTool(BaseTool):
    """
    A generic, database-configurable tool for performing CRUD (Create, Read/Fetch, Update, Delete)
    operations on Supabase tables.

    Instances of this tool are configured via database entries in the 'agent_tools' table.
    The 'config' column (JSONB) for each tool entry specifies:
    - 'table_name': The target Supabase table.
    - 'method': The CRUD operation ('create', 'fetch', 'update', 'delete').
    - 'field_map': (For 'create'/'update') A mapping from LLM input fields to database column names.
    - 'runtime_args_schema': A JSON schema defining the expected 'data' and 'filters' arguments
                               for the LLM, from which a Pydantic model is dynamically generated
                               to become this tool instance's 'args_schema'.

    The tool's 'name' and 'description' (for the LLM) are also sourced from the database.
    Mandatory 'user_id' (and 'agent_name' for some tables) are automatically applied as filters
    or injected into data payloads to ensure data scoping and security.
    """
    # Pydantic model configuration for the tool's own class structure
    model_config = ConfigDict(extra='ignore', arbitrary_types_allowed=True)

    # --- Fields populated by Pydantic from constructor_kwargs in agent_loader_db.py ---
    user_id: str = Field(description="The ID of the user performing the operation. Automatically applied for data scoping.")
    agent_name: str = Field(description="The name of the agent invoking the tool. Used for logging and potentially for agent-specific data scoping.")
    supabase_url: str = Field(description="The Supabase project URL, injected at instantiation.")
    supabase_key: str = Field(description="The Supabase service key (or anon key if appropriate), injected at instantiation.")
    
    table_name: str = Field(description="The target Supabase table name, specified in the DB tool config.")
    method: str = Field(description="The CRUD method ('create', 'fetch', 'update', 'delete'), specified in the DB tool config.")
    field_map: Dict[str, str] = Field(
        default_factory=dict, 
        description="A mapping from keys in the LLM-provided 'data' argument to actual database column names. Used for 'create' and 'update' methods. Specified in the DB tool config."
    )
    # apply_agent_name_filter: bool = Field(
    #     default=False, 
    #     description="If true, 'agent_name' will be added as a filter for non-LTM tables. Configured in DB tool config."
    # ) # Re-add if making agent_name filtering fully config-driven

    # args_schema is a ClassVar in BaseTool. Specific instances are typically of a dynamically
    # created subclass that has its own args_schema overriding this default.
    # The loader (_create_dynamic_crud_tool_class) sets this on the dynamic subclass.
    args_schema: ClassVar[Type[BaseModel]] = CRUDToolInput 
    
    _db_client: Any = None # Supabase client instance, initialized in _init_db_client

    def __init__(self, **kwargs: Any):
        """
        Initializes the CRUDTool.
        
        All Pydantic fields defined on this class (user_id, agent_name, supabase_url, 
        supabase_key, table_name, method, field_map) are populated by Pydantic 
        when `super().__init__(**kwargs)` is called, using values passed from the 
        agent loader. The 'name' and 'description' for the BaseTool are also passed 
        via kwargs.

        If the agent loader provided a 'runtime_args_schema', it will have created a 
        dynamic subclass of CRUDTool with a specific `args_schema` set as a class
        variable on that subclass. This instance will therefore be of that dynamic
        subclass.
        """
        super().__init__(**kwargs)
        
        logger.debug(
            f"CRUDTool '{self.name}' (instance of {self.__class__.__name__}) initialized. Method: '{self.method}', Table: '{self.table_name}'. "
            f"Effective args_schema: '{type(self).args_schema.__name__}'. Field map: {self.field_map}"
        )

        self._db_client = None # Ensure it's None before attempting initialization
        try: 
            self._init_db_client()
        except Exception as e:
            # Log and allow continuation; _run will check _db_client and raise if still None.
            logger.error(f"CRUDTool '{self.name}': Supabase client initialization failed during __init__: {e}", exc_info=True)

    def _init_db_client(self):
        """Initializes the Supabase client instance for the tool."""
        if not self.supabase_url or not self.supabase_key:
            logger.error(f"CRUDTool '{self.name}': Supabase URL or key is missing. Cannot initialize Supabase client.")
            # self._db_client remains None
            return 
        try:
            self._db_client = create_client(self.supabase_url, self.supabase_key)
            logger.debug(f"CRUDTool '{self.name}': Supabase client initialized successfully for table '{self.table_name}'.")
        except Exception as e:
            logger.error(f"CRUDTool '{self.name}': Supabase client initialization failed: {e}", exc_info=True)
            self._db_client = None # Ensure client is None if initialization fails

    def _ensure_dict_input(self, input_val: Optional[Any], arg_name: str) -> Optional[Dict[str, Any]]:
        """
        Ensures that an input argument (expected to be 'data' or 'filters') is a dictionary.
        If `input_val` is a Pydantic BaseModel instance, it's converted to a dictionary.
        If it's already a dictionary or None, it's returned as is.
        Otherwise, a ToolException is raised.

        Args:
            input_val: The input value to check/convert.
            arg_name: The name of the argument ('data' or 'filters'), for error messages.

        Returns:
            The input value as a dictionary, or None if the input was None.

        Raises:
            ToolException: If `input_val` is not a BaseModel, dict, or None.
        """
        if isinstance(input_val, BaseModel):
            logger.debug(f"CRUDTool '{self.name}': Converting argument '{arg_name}' from Pydantic model ({type(input_val).__name__}) to dict.")
            return input_val.model_dump(exclude_unset=True)
        elif isinstance(input_val, dict) or input_val is None:
            return input_val
        else:
            raise ToolException(
                f"Agent Error: For tool '{self.name}', argument '{arg_name}' must be a dictionary, Pydantic model, or None. Received type: {type(input_val).__name__}"
            )

    def _validate_runtime_inputs(self, data: Optional[Any], filters: Optional[Any] = None):
        """
        Validates the processed 'data' and 'filters' arguments (now ensured to be dicts or None)
        based on the CRUD method.

        - For 'create' and 'update': 'data' dictionary must be provided and non-empty.
        - For 'update' and 'delete': 'filters' dictionary must be provided and contain an 'id' key.
        - For 'fetch': Specific filter requirements (like needing an 'id') are primarily enforced
                       by the dynamically generated 'args_schema' (via Pydantic validation before this
                       method is called) based on the tool's DB configuration. This method does not
                       add further generic validation for 'fetch' filters.

        Args:
            data: The 'data' argument, processed by _ensure_dict_input.
            filters: The 'filters' argument, processed by _ensure_dict_input.

        Raises:
            ToolException: If validation rules are violated.
        """
        logger.debug(f"CRUDTool '{self.name}': Validating runtime inputs (now dicts or None). Method: '{self.method}'. Data: {data}, Filters: {filters}")

        data_dict = self._ensure_dict_input(data, "data") # Should already be dicts from _run, but safe to re-ensure
        filters_dict = self._ensure_dict_input(filters, "filters")

        if self.method in ["create", "update"]:
            if data_dict is None:
                raise ToolException(f"Agent Error: Input 'data' (a dictionary) is required for '{self.method}' operation using tool '{self.name}'.")
            if not data_dict: # Checks if the dictionary is empty
                raise ToolException(f"Agent Error: Input 'data' for '{self.method}' operation using tool '{self.name}' cannot be an empty dictionary.")
    
        if self.method in ["update", "delete"]:
            if filters_dict is None or filters_dict.get("id") is None:
                raise ToolException(
                    f"Agent Error: For '{self.method}' operations with tool '{self.name}', the 'filters' argument must be a dictionary "
                    f"containing an 'id' key to target the specific record for modification or deletion."
                )
        
        logger.debug(f"CRUDTool '{self.name}': Runtime input validation completed successfully.")
            
    def _apply_mandatory_filters(self, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applies mandatory filters to the provided filter dictionary.
        Currently, 'user_id' is always added.
        'agent_name' is added as a filter if the table is NOT 'agent_long_term_memory' 
        and the tool instance has an agent_name. This table-specific logic is a candidate
        for future refactoring to be configuration-driven.

        Args:
            filters: The initial dictionary of filters provided by the LLM (or None).

        Returns:
            A new dictionary with mandatory filters applied.
        """
        final_filters = filters.copy() if filters else {}
        final_filters["user_id"] = self.user_id # Always scope by user_id
        
        # Original logic: Add agent_name as a filter for tables other than agent_long_term_memory
        if self.table_name != "agent_long_term_memory":
            if hasattr(self, 'agent_name') and self.agent_name: # Ensure agent_name exists and is not empty
                 final_filters["agent_name"] = self.agent_name
        
        logger.debug(f"CRUDTool '{self.name}': Applied mandatory filters. Initial: {filters}, Final: {final_filters}")
        return final_filters
    
    def _apply_mandatory_fields(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conceptually ensures mandatory fields like 'user_id' and 'agent_name' are part of the data
        payload for 'create' or 'update' operations if they are actual columns in the table.
        This method is largely superseded by `_prepare_data_payload` which explicitly adds
        `user_id` and `agent_name` to the payload if they are configured for the table
        (which they usually are for scoping).

        Args:
            agent_data: The data dictionary from the LLM.

        Returns:
            The data dictionary, potentially with 'user_id' and 'agent_name' added if they were
            part of the original design to be directly in the payload.
        """
        # This method's direct utility is reduced since _prepare_data_payload handles adding user_id/agent_name.
        # It's kept for potential future use if direct data injection patterns re-emerge.
        prepared_data = agent_data.copy() if agent_data else {}
        # Example: If user_id and agent_name were meant to be part of the main payload directly:
        # prepared_data["user_id"] = self.user_id 
        # if hasattr(self, 'agent_name') and self.agent_name:
        #     prepared_data["agent_name"] = self.agent_name
        logger.debug(f"CRUDTool '{self.name}': (_apply_mandatory_fields) Conceptual mandatory fields processing. Input: {agent_data}, Output: {prepared_data}")
        return prepared_data

    def _prepare_data_payload(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepares the final data payload for 'create' or 'update' operations.
        1. Applies the 'field_map' to translate LLM input keys to database column names.
        2. Ensures 'user_id' is in the payload.
        3. Adds 'agent_name' to the payload if the table is not 'agent_long_term_memory' 
           (and agent_name is available).
        4. Validates that the mapping results in a non-empty set of meaningful fields.

        Args:
            agent_data: The data dictionary from the LLM's 'data' argument.

        Returns:
            A dictionary ready to be sent as the data payload to Supabase.

        Raises:
            ToolException: If `agent_data` is empty, or if field mapping results in no usable
                           database fields, or if no meaningful data is left after mapping.
        """
        if not agent_data: 
            raise ToolException(f"Internal Error: '_prepare_data_payload' called with empty 'agent_data' for '{self.method}' operation in tool '{self.name}'.")

        db_payload: Dict[str, Any]
        if self.field_map:
            db_payload = {
                self.field_map[k]: v 
                for k, v in agent_data.items() 
                if k in self.field_map
            }
            if not db_payload and agent_data: 
                raise ToolException(
                    f"Agent Error: Data provided for tool '{self.name}' (keys: {list(agent_data.keys())}) "
                    f"did not map to any database columns using field_map: {self.field_map}. "
                    f"Ensure input data keys match keys in 'field_map'."
                )
        else: 
            db_payload = agent_data.copy()
            logger.debug(f"CRUDTool '{self.name}': No field_map provided. Using agent data keys directly for DB payload: {list(db_payload.keys())}")

        db_payload["user_id"] = self.user_id
        
        # Original logic: Add agent_name to payload for tables other than agent_long_term_memory
        if self.table_name != "agent_long_term_memory":
            if hasattr(self, 'agent_name') and self.agent_name:
                db_payload["agent_name"] = self.agent_name
        
        # Check if there are any meaningful keys in the payload other than user_id/agent_name,
        # UNLESS it's agent_long_term_memory, in which case agent_name itself might be a meaningful field
        # if it were part of the field_map (e.g. if LTMs were per-agent rather than per-user).
        # Current LTM table doesn't have agent_name, so this complexity is less relevant for it now.
        meaningful_db_keys = [
            k for k in db_payload.keys() 
            if k not in ("user_id", "agent_name") or \
               (k == "agent_name" and self.table_name == "agent_long_term_memory" and "agent_name" in (self.field_map or {}).values()) # only if agent_name is an actual mapped DB field for LTM
        ]
        # A simpler check if agent_name is NOT a column in LTM and generally not directly settable by LLM for LTM:
        # meaningful_db_keys = [k for k in db_payload.keys() if k not in ("user_id", "agent_name")]
        # if self.table_name == "agent_long_term_memory" and "agent_name" in db_payload and "agent_name" in (self.field_map.values() if self.field_map else []):
        #    pass # agent_name might be a legitimate field for LTM if field_mapped

        # Revised meaningful_db_keys check based on typical structure: 
        # user_id and agent_name (if added by the tool) are scoping fields, not primary data from LLM.
        # Check if any *other* keys exist, or if agent_name was part of the original agent_data AND field_mapped for LTM.
        keys_from_llm_data_or_mapped = set((self.field_map or agent_data).keys() if self.field_map else agent_data.keys())
        
        # What are the actual database columns we are trying to set, apart from user_id/agent_name auto-added?
        intended_payload_columns = set(db_payload.keys()) - {"user_id", "agent_name"}
        # If agent_name was in the original data from LLM (via field_map), it's intended.
        if "agent_name" in db_payload and self.field_map.get("agent_name") == "agent_name": # Simplified: if agent_name was mapped to agent_name
            intended_payload_columns.add("agent_name")
        elif "agent_name" in db_payload and not self.field_map and "agent_name" in agent_data:
            intended_payload_columns.add("agent_name") # No field map, agent_name was in original data

        if not intended_payload_columns:
            logger.error(
                f"CRUDTool '{self.name}' (data preparation): No meaningful data fields after mapping/direct use and scoping ID enforcement. "
                f"Original agent_data keys: {list(agent_data.keys())}, Current DB Payload keys: {list(db_payload.keys())}, Field map: {self.field_map}"
            )
            raise ToolException(
                f"Agent Error: Data provided for tool '{self.name}' (input keys: {list(agent_data.keys())}) "
                f"results in no updatable/insertable fields beyond automatically added scoping IDs (user_id, agent_name). "
                f"Check 'field_map' and input data structure."
            )
            
        logger.debug(f"CRUDTool '{self.name}': Prepared DB payload for '{self.method}': {db_payload}")
        return db_payload

    def _run(self, data: Optional[Any] = None, filters: Optional[Any] = None) -> str:
        """
        Executes the configured CRUD operation.

        Workflow:
        1. Ensures Supabase client is initialized.
        2. Ensures 'data' and 'filters' (if provided as Pydantic models) are dicts.
        3. Validates these dicts using `_validate_runtime_inputs`.
        4. Applies mandatory filters (e.g., user_id) using `_apply_mandatory_filters`.
        5. For 'create'/'update', prepares the data payload using `_prepare_data_payload`.
        6. Constructs and executes the Supabase query based on `self.method`.
        7. Formats and returns the result or error message.

        Args:
            data: The 'data' argument from the LLM, conforming to the tool's (dynamic) args_schema.
            filters: The 'filters' argument from the LLM, conforming to the tool's (dynamic) args_schema.

        Returns:
            A string summarizing the outcome of the operation (e.g., "Created: [...]", 
            "Fetched X record(s): [...]", or an error message).

        Raises:
            ToolException: For validation errors, internal errors, or database operation failures.
        """
        logger.debug(f"CRUDTool '{self.name}': _run invoked. Original Data type: {type(data)}, Original Filters type: {type(filters)}")
        if self._db_client is None:
            logger.error(f"CRUDTool '{self.name}': Supabase client not initialized. Cannot execute method '{self.method}'.")
            raise ToolException(f"Internal Error: Supabase client not initialized for tool '{self.name}'.")

        data_for_processing = self._ensure_dict_input(data, "data")
        filters_for_processing = self._ensure_dict_input(filters, "filters")
        
        logger.debug(f"CRUDTool '{self.name}' in _run: Processed data_for_processing type: {type(data_for_processing)}, filters_for_processing type: {type(filters_for_processing)}")

        try:
            self._validate_runtime_inputs(data_for_processing, filters_for_processing)
        except ToolException as e: 
            logger.info(f"CRUDTool '{self.name}': Input validation failed: {e}") # Log as info, error will be propagated
            raise 
        
        final_filters = self._apply_mandatory_filters(filters_for_processing)
        final_data_payload: Optional[Dict[str, Any]] = None
        
        if self.method in ["create", "update"]:
            try:
                final_data_payload = self._prepare_data_payload(data_for_processing)
            except ToolException as e:
                logger.info(f"CRUDTool '{self.name}': Data payload preparation failed: {e}") # Log as info, error will be propagated
                raise

        try:
            logger.info(
                f"CRUDTool '{self.name}': Executing method '{self.method}' on table '{self.table_name}'. "
                f"\nFinal Data Payload (for create/update): {final_data_payload if self.method in ['create', 'update'] else 'N/A'}"
                f"\nFinal Filters: {final_filters}"
            )
            
            table = self._db_client.table(self.table_name)
            query_response = None # Stores the result of .execute()
            DEFAULT_FETCH_LIMIT = 25 
            
            if self.method == "create":
                query_response = table.insert(final_data_payload).execute()
            
            elif self.method == "fetch":
                query_builder = table.select("*")
                # _apply_filters_to_supabase_query was reverted by user, applying manually
                for k, v_val in final_filters.items():
                    query_builder = query_builder.eq(k, v_val)
                query_builder = query_builder.limit(DEFAULT_FETCH_LIMIT).order("updated_at", desc=True) # Assumes 'updated_at' exists
                query_response = query_builder.execute()

            elif self.method == "update":
                query_builder = table.update(final_data_payload)
                for k, v_val in final_filters.items(): 
                    query_builder = query_builder.eq(k, v_val)
                query_response = query_builder.execute()

            elif self.method == "delete":
                query_builder = table.delete()
                for k, v_val in final_filters.items():
                    query_builder = query_builder.eq(k, v_val)
                query_response = query_builder.execute()
            
            else: 
                raise ToolException(f"Internal Error: Unhandled method '{self.method}' during execution for tool '{self.name}'. Should be caught by earlier validation if method name is constrained (e.g., Enum).")

            response_data = query_response.data

            if self.method == "fetch" and not response_data:
                return f"No records found matching your criteria in table '{self.table_name}'." # More specific table name
            
            action_map = {
                "create": "Created",
                "fetch": f"Fetched {len(response_data) if response_data else 0} record(s)",
                "update": "Updated",
                "delete": "Deleted"
            }
            action_string = action_map.get(self.method, "Processed") # Default if method somehow unexpected
            
            return f"{action_string}: {response_data}"

        except Exception as e:
            # More detailed logging for database errors
            logger.error(f"CRUDTool '{self.name}': Database operation error during '{self.method}' on table '{self.table_name}'. Filters: {final_filters}, Payload: {final_data_payload}. Error: {e}", exc_info=True)
            error_message_prefix = f"Database operation failed for tool '{self.name}'"
            if hasattr(e, 'json') and callable(e.json): # Attempt to parse Postgrest error
                try:
                    error_details = e.json()
                    message = error_details.get('message', str(e))
                    code = error_details.get('code', 'N/A')
                    hint = error_details.get('hint')
                    details_str = error_details.get('details')
                    error_summary = f"DB Error (Code: {code}): {message}"
                    if hint: error_summary += f". Hint: {hint}"
                    if details_str: error_summary += f". Details: {details_str}"
                    raise ToolException(f"{error_message_prefix}. {error_summary}")
                except Exception as json_e: # Fallback if JSON parsing fails
                    logger.warning(f"CRUDTool '{self.name}': Could not parse detailed JSON from database error: {json_e}")
            # Generic fallback if not a Postgrest error or JSON parsing failed
            raise ToolException(f"{error_message_prefix}. Error type: {type(e).__name__}, Details: {str(e)}.")

    async def _arun(self, data: Optional[Dict[str, Any]] = None, filters: Optional[Dict[str, Any]] = None) -> str:
        """
        Asynchronous version of the tool's execution logic.
        Currently defers to the synchronous `_run` method.
        Langchain's `BaseTool` will wrap this in `asyncio.to_thread` if called in an async context.
        Ensure `_run` is thread-safe if it were to perform complex CPU-bound tasks or shared state mutation
        (though for Supabase client calls, it's mostly I/O bound and client instances are per-tool).

        Args:
            data: The 'data' argument, expected as a dictionary.
            filters: The 'filters' argument, expected as a dictionary.

        Returns:
            A string summarizing the outcome.
        """
        # Note: Type hints for data/filters are Dict here, as BaseTool's _arun/_run plumbing
        # often passes them as dicts after Pydantic model validation and conversion.
        # The _ensure_dict_input in _run handles cases where they might still be BaseModels
        # if called directly or through a different path.
        logger.debug(f"CRUDTool '{self.name}': _arun called. Deferring to synchronous _run. Data type: {type(data)}, Filters type: {type(filters)}")
        return self._run(data=data, filters=filters) 