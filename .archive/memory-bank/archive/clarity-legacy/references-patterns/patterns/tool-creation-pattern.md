# Tool Creation and Configuration Pattern for Clarity Agents

**Owner:** AI Agent & Development Team  
**Status:** Implemented & Evolving  
**Created:** 2025-05-24 (Original Pattern)
**Last Updated:** 2025-07-03 (Reflects DB-Driven CRUDTool Configuration)

---

## 1. Introduction

This document outlines the standardized pattern for creating and configuring tools within the Clarity agent ecosystem. The goal is to ensure maintainability, extensibility, and consistency. Tools are modular, reusable capabilities that can be attached to agents and are invoked by the agent runtime. This pattern primarily focuses on leveraging a generic `CRUDTool` for database operations, configured via the database itself.

---

## 2. Core Tool: The Generic `CRUDTool`

Instead of creating numerous Python subclasses for each specific CRUD (Create, Read/Fetch, Update, Delete) operation on different database tables, we primarily use a single, highly configurable generic tool: `src.core.tools.crud_tool.CRUDTool`.

### 2.1. `CRUDTool` Capabilities

- **Generic Operations:** Can perform 'create', 'fetch', 'update', or 'delete' operations.
- **Database Driven:** Each specific "tool" instance (e.g., "create_new_task", "fetch_user_notes") is defined as a row in the `agent_tools` database table.
- **Dynamic Argument Schemas:** The `CRUDTool` instances have their `args_schema` (defining what arguments the LLM should provide, like `data` and `filters`) dynamically generated at runtime based on a `runtime_args_schema` JSON configuration stored in the database. This allows for tailored input validation and clear LLM guidance for each specific operation.
- **Automatic Scoping:** Automatically applies `user_id` for data scoping. Other context like `agent_name` can also be involved in filtering or data payload, based on configuration (currently partially hardcoded, aiming for full config-driven).

### 2.2. How `CRUDTool` is Instantiated by the Loader (`agent_loader_db.py`)

1.  The `agent_loader_db.py` fetches tool configurations from the `agent_tools` table.
2.  For entries where `type` is "CRUDTool":
    a.  It reads the `name`, `description`, and the JSONB `config` column.
    b.  The `config` column provides:
        *   `table_name`: The target Supabase table.
        *   `method`: The CRUD operation type string ("create", "fetch", "update", "delete").
        *   `field_map` (dict, optional): For 'create'/'update', maps keys from the LLM's input `data` argument to actual database column names.
        *   `runtime_args_schema` (JSON object): Defines the structure for the `data` and `filters` arguments the LLM should use. This includes field names, their types (str, int, dict, bool, list), optionality, descriptions, and even nested object structures.
    c.  If `runtime_args_schema` is present, the loader dynamically creates a new Python class that inherits from `CRUDTool`. It generates a Pydantic model from `runtime_args_schema` and sets it as the `args_schema` class variable on this new dynamic class.
    d.  The tool instance is then created from this (potentially dynamic) class, injecting `user_id`, `agent_name`, Supabase details, and the operational parameters (`table_name`, `method`, `field_map`) from the DB config.

---

## 3. Configuring a New "CRUD Tool Instance" in the Database

To add a new capability like "fetching project details" or "creating a new user setting", you add a new row to the `agent_tools` table. No new Python subclass of `CRUDTool` is typically needed.

**Steps:**

1.  **Identify Operation:**
    *   What **table** will it operate on? (e.g., `projects`, `user_settings`)
    *   What **method** will it use? (`create`, `fetch`, `update`, `delete`)

2.  **Define LLM Interaction (`name`, `description`, `runtime_args_schema`):**
    *   **`name` (string):** A concise, descriptive name for the Langchain tool (e.g., `fetch_project_by_id`, `create_user_setting_for_notifications`). This is what the LLM refers to.
    *   **`description` (string):** Clear instructions for the LLM. Explain what the tool does, when to use it, and critically, *how to structure the `data` and/or `filters` arguments*. This description should align perfectly with the `runtime_args_schema`.
    *   **`runtime_args_schema` (JSON object):** This is the contract for the LLM's input.
        *   It defines the top-level arguments the tool instance will accept (typically `data` for inputs to create/update, and `filters` for specifying records in fetch/update/delete).
        *   For each argument (e.g., `data`), define its `type` (usually "dict"), `optional` (boolean), `description`, and if it's a dict, its `properties`.
        *   `properties` further define nested fields, each with its `type` (string, int, bool, list, dict), `optional` status, and `description`.
        *   **Example `runtime_args_schema` for a "create memory" tool:**
            ```json
            {
              "data": {
                "type": "dict",
                "optional": false,
                "description": "The data for the new memory. Must contain a 'memory_content' field.",
                "properties": {
                  "memory_content": {
                    "type": "str",
                    "optional": false,
                    "description": "The actual text content of the memory to save."
                  }
                }
              }
            }
            ```
        *   **Example `runtime_args_schema` for a "fetch memory by ID" tool:**
            ```json
            {
              "filters": {
                "type": "dict",
                "optional": false,
                "description": "Filters to specify the memory. Must contain an 'id'.",
                "properties": {
                  "id": {
                    "type": "str",
                    "optional": false,
                    "description": "The UUID of the memory to fetch."
                  }
                }
              }
            }
            ```
        *   **Example `runtime_args_schema` for a "fetch all memories (LTM)" tool:**
            ```json
            {
              "filters": {
                "type": "dict",
                "optional": true, // Filters argument itself is optional for fetch-all
                "description": "Optional. Filters to specify memories. If omitted, fetches all accessible memories. If provided, can filter by 'id'.",
                "properties": {
                  "id": {
                    "type": "str",
                    "optional": true, // ID within filters is also optional
                    "description": "Optional. The UUID of a specific memory to fetch."
                  }
                }
              }
            }
            ```

3.  **Define Data Mapping (if applicable):**
    *   **`field_map` (JSON object, in `config`):** If the `method` is `create` or `update`, and the keys in your LLM's input `data` argument (defined in `runtime_args_schema.data.properties`) are different from your database column names, provide a `field_map`.
        *   Example: `{"llm_input_key": "db_column_name", "memory_text": "notes"}`.
        *   If not provided, `CRUDTool` assumes LLM input keys directly match DB column names.

4.  **Construct the `config` JSONB Column:**
    This JSON object in the `config` field of your `agent_tools` row will contain:
    ```json
    {
      "table_name": "your_table_name",
      "method": "your_method", // "create", "fetch", "update", or "delete"
      "field_map": { /* if needed, e.g., {"input_field": "db_column"} */ },
      "runtime_args_schema": { /* your detailed schema structure here */ }
      // Optional future: "apply_agent_name_filter": true/false 
    }
    ```

5.  **Add Row to `agent_tools` Table:**
    *   `id`: (auto-generated UUID)
    *   `agent_id`: Foreign key to the `agent_configurations` table (the agent this tool instance belongs to).
    *   `type`: **"CRUDTool"** (This string must match a key in `TOOL_REGISTRY` in `agent_loader_db.py`).
    *   `name`: Your chosen Langchain tool name (e.g., "create_agent_long_term_memory").
    *   `description`: Your detailed description for the LLM.
    *   `config`: The JSONB object constructed in the previous step.
    *   `is_active`: `true` (boolean).
    *   `order`: (integer, optional) for ordering tools in UI or prompts.
    *   `created_at`, `updated_at`: (auto-managed timestamps).

---

## 4. Non-CRUD Tools (Custom Python Classes)

If a tool's functionality does not fit the CRUD pattern (e.g., it calls an external API, performs complex calculations, has very unique state management):

1.  **Implement the Tool Class:**
    *   Create a new Python class that inherits from `langchain_core.tools.BaseTool`.
    *   Define its `name`, `description`, and `args_schema` (a Pydantic model for its inputs).
    *   Implement the `_run()` method (and optionally `_arun()` for async).
    *   Ensure its `__init__` method can accept `user_id`, `agent_name`, `supabase_url`, `supabase_key` if needed for context or its own operations, plus any parameters from its DB `config`.

2.  **Register the Tool Class:**
    *   Add your new class to the `TOOL_REGISTRY` dictionary in `src/core/agent_loader_db.py`.
        ```python
        TOOL_REGISTRY = {
            "CRUDTool": CRUDTool,
            "MyCustomToolPythonClassName": MyCustomToolPythonClassName 
        }
        ```

3.  **Add Row to `agent_tools` Table:**
    *   `type`: The string key you used in `TOOL_REGISTRY` (e.g., "MyCustomToolPythonClassName").
    *   `name`: Langchain tool name.
    *   `description`: Description for the LLM.
    *   `config`: (JSONB, optional) Any static configuration parameters your custom tool's `__init__` method expects. These will be passed as keyword arguments during instantiation.
    *   Other fields as above (`agent_id`, `is_active`, etc.).

---

## 5. Benefits of the DB-Driven `CRUDTool` Pattern

- **Reduced Python Code:** No need to write a new Python class for most common database operations.
- **Configuration over Code:** Tool behavior, especially input schemas, is defined in the database, making it easier to iterate and manage without deployments for schema changes.
- **Dynamic & Flexible:** `runtime_args_schema` allows for rich, validated inputs tailored to each specific operation.
- **Centralized Logic:** The core CRUD logic resides in `CRUDTool`, promoting consistency.
- **Clear Contract:** The `runtime_args_schema` and tool `description` form a clear contract for the LLM.

---

## 6. Future Considerations

- **Fully Config-Driven Scoping:** Make `agent_name` filtering/payload inclusion for `CRUDTool` entirely driven by a flag in the DB `config` rather than table name comparisons.
- **Schema Validation for `config`:** Implement validation for the structure of the `config` JSONB object itself (e.g., using a Pydantic model when loading/saving tool configurations).
- **More Sophisticated Type Handling:** Enhance `_create_dynamic_crud_tool_class` to support more Pydantic types (e.g., Enums, specific List types like `List[str]`) based on the `runtime_args_schema`.

---

## 7. Example: Agent Long Term Memory Tools

```python
from core.tools.crud_tool import CRUDTool, CRUDToolInput

class CreateAgentLongTermMemoryTool(CRUDTool):
    name = "create_agent_long_term_memory"
    description = "Creates a new agent long-term memory record. Requires 'notes' in data."
    args_schema = CRUDToolInput
    def __init__(self, user_id, agent_id, supabase_url, supabase_key, **kwargs):
        super().__init__(
            table_name="agent_long_term_memory",
            method="create",
            user_id=user_id,
            agent_id=agent_id,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            field_map={"notes": "notes"},
            **kwargs
        )

class FetchAgentLongTermMemoryTool(CRUDTool):
    name = "fetch_agent_long_term_memory"
    description = "Fetches agent long-term memory records. Use filters to narrow results."
    args_schema = CRUDToolInput
    def __init__(self, user_id, agent_id, supabase_url, supabase_key, **kwargs):
        super().__init__(
            table_name="agent_long_term_memory",
            method="fetch",
            user_id=user_id,
            agent_id=agent_id,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            **kwargs
        )

class UpdateAgentLongTermMemoryTool(CRUDTool):
    name = "update_agent_long_term_memory"
    description = "Updates agent long-term memory records. Requires 'notes' in data and filters."
    args_schema = CRUDToolInput
    def __init__(self, user_id, agent_id, supabase_url, supabase_key, **kwargs):
        super().__init__(
            table_name="agent_long_term_memory",
            method="update",
            user_id=user_id,
            agent_id=agent_id,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            field_map={"notes": "notes"},
            **kwargs
        )

class DeleteAgentLongTermMemoryTool(CRUDTool):
    name = "delete_agent_long_term_memory"
    description = "Deletes agent long-term memory records. Requires filters."
    args_schema = CRUDToolInput
    def __init__(self, user_id, agent_id, supabase_url, supabase_key, **kwargs):
        super().__init__(
            table_name="agent_long_term_memory",
            method="delete",
            user_id=user_id,
            agent_id=agent_id,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            **kwargs
        )
```

---

## 8. DB Configuration Example

- **tool_type**: Should match the class name in your registry (e.g., `"CreateAgentLongTermMemoryTool"`).
- **tool_config**:
  - For create/update: `{ "field_map": { "notes": "notes" } }`
  - For fetch/delete: `{}`

---

## 9. Checklist for Adding a New CRUD Tool

1. **Implement the tool class** as a subclass of `CRUDTool` for a single operation.
2. **Register the tool** in `TOOL_REGISTRY` in `src/core/agent_loader_db.py`.
3. **Add a DB row** in `agent_tools` with the correct `tool_type` and `tool_config`.
4. **(Optional) Add tests** for the tool's logic.
5. **(Optional) Document** the tool's purpose and config options.

---

## 10. Next Steps

- **Refine this pattern** as new tool types or requirements emerge.
- **Encourage contributions** to the tool registry and documentation.
- **Automate validation** of tool config (optional future enhancement). 