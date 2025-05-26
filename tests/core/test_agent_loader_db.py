import unittest
from unittest.mock import MagicMock, patch, call # Added call
import os
import logging
import json
from typing import Dict, Any, List, Optional, Type # Added Type

from pydantic import BaseModel, Field, ConfigDict
from langchain_core.tools import BaseTool

# Modules to test
from src.core.agent_loader_db import (
    TOOL_REGISTRY,
    _create_dynamic_crud_tool_class,
    _create_dynamic_args_model,
    load_tools_from_db,
    load_agent_executor_db
)
from core.tools.crud_tool import CRUDTool, CRUDToolInput # For comparison and base class
from src.core.agents.customizable_agent import CustomizableAgentExecutor

# Basic logger for tests
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG) # Use DEBUG for more verbose test output if needed

# --- Mock Tool for TOOL_REGISTRY --- 
class SampleNonCRUDTool(BaseTool):
    name: str = "sample_non_crud_tool"
    description: str = "A sample non-CRUD tool for testing."
    user_id: Optional[str] = None
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    custom_config_param: Optional[str] = None

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        return f"SampleNonCRUDTool executed with {self.custom_config_param}"

class TestCreateDynamicArgsModel(unittest.TestCase):
    def test_create_simple_model(self):
        model_name = "SimpleTestModel"
        properties_config = {
            "name": {"type": "str", "optional": False, "description": "A name"},
            "age": {"type": "int", "optional": True, "description": "An age"}
        }
        DynamicModel = _create_dynamic_args_model(model_name, properties_config)
        self.assertEqual(DynamicModel.__name__, model_name)
        
        # Check fields (Pydantic v2 uses model_fields)
        self.assertIn("name", DynamicModel.model_fields)
        self.assertEqual(DynamicModel.model_fields["name"].annotation, str)
        self.assertTrue(DynamicModel.model_fields["name"].is_required())
        self.assertEqual(DynamicModel.model_fields["name"].description, "A name")

        self.assertIn("age", DynamicModel.model_fields)
        self.assertEqual(DynamicModel.model_fields["age"].annotation, Optional[int])
        self.assertFalse(DynamicModel.model_fields["age"].is_required())
        self.assertEqual(DynamicModel.model_fields["age"].description, "An age")

    def test_create_model_with_dict_and_list(self):
        properties_config = {
            "metadata": {"type": "dict", "optional": False},
            "tags": {"type": "list", "optional": True}
        }
        DynamicModel = _create_dynamic_args_model("ComplexModel", properties_config)
        self.assertEqual(DynamicModel.model_fields["metadata"].annotation, Dict[str, Any])
        self.assertEqual(DynamicModel.model_fields["tags"].annotation, Optional[List[Any]])

    def test_empty_properties_config(self):
        DynamicModel = _create_dynamic_args_model("EmptyPropsModel", {})
        self.assertEqual(len(DynamicModel.model_fields), 0)
        # Check if it falls back to EmptyNestedModel behavior
        self.assertTrue(issubclass(DynamicModel, BaseModel))
        # Test instantiation of the fallback model
        instance = DynamicModel()
        self.assertIsNotNone(instance)

    def test_invalid_property_config_item(self):
        properties_config = {
            "valid_field": {"type": "str"},
            "invalid_field": "not_a_dict" 
        }
        DynamicModel = _create_dynamic_args_model("InvalidItemModel", properties_config)
        self.assertIn("valid_field", DynamicModel.model_fields)
        self.assertNotIn("invalid_field", DynamicModel.model_fields)
        self.assertEqual(len(DynamicModel.model_fields), 1)


class TestCreateDynamicCRUDToolClass(unittest.TestCase):
    def test_create_dynamic_class_with_schema(self):
        tool_name_from_db = "MyDynamicTool"
        runtime_schema_config = {
            "data": {
                "type": "dict", "optional": False, "description": "Data to create/update.",
                "properties": {
                    "item_name": {"type": "str", "optional": False, "description": "Name of the item."},
                    "item_value": {"type": "int", "optional": True, "description": "Value of the item."}
                }
            },
            "filters": {
                "type": "dict", "optional": True, "description": "Filters for query/delete.",
                "properties": {"filter_id": {"type": "str", "optional": False}}
            }
        }
        DynamicToolClass = _create_dynamic_crud_tool_class(tool_name_from_db, CRUDTool, runtime_schema_config)
        
        self.assertTrue(issubclass(DynamicToolClass, CRUDTool))
        self.assertNotEqual(DynamicToolClass, CRUDTool) # Ensure it's a new class
        self.assertTrue(hasattr(DynamicToolClass, 'args_schema'))
        self.assertNotEqual(DynamicToolClass.args_schema, CRUDToolInput) # Ensure schema is different
        
        # Check the generated args_schema fields
        args_schema = DynamicToolClass.args_schema
        self.assertIn("data", args_schema.model_fields)
        self.assertTrue(args_schema.model_fields["data"].is_required())
        data_field_type = args_schema.model_fields["data"].annotation
        self.assertTrue(issubclass(data_field_type, BaseModel)) # Nested model for data
        self.assertIn("item_name", data_field_type.model_fields)
        self.assertEqual(data_field_type.model_fields["item_name"].annotation, str)

        self.assertIn("filters", args_schema.model_fields)
        self.assertFalse(args_schema.model_fields["filters"].is_required())
        filters_field_type = args_schema.model_fields["filters"].annotation # This is Optional[NestedModel]
        # Pydantic v2: Optional[T] means type(T) is the actual model for .annotation on Optional fields
        # For Optional[NestedModel], the .annotation will be the NestedModel itself if we inspect correctly.
        # However, to get the actual model type from Optional[T], we need to look at args of typing.Union
        self.assertTrue(issubclass(filters_field_type.__args__[0], BaseModel) if hasattr(filters_field_type, '__args__') else issubclass(filters_field_type, BaseModel))
        actual_filter_model = filters_field_type.__args__[0] if hasattr(filters_field_type, '__args__') else filters_field_type
        self.assertIn("filter_id", actual_filter_model.model_fields)

    def test_fallback_to_base_schema_if_config_empty(self):
        DynamicToolClass = _create_dynamic_crud_tool_class("EmptySchemaTool", CRUDTool, {})
        self.assertEqual(DynamicToolClass, CRUDTool) # Should return the base class itself
        self.assertEqual(DynamicToolClass.args_schema, CRUDToolInput)

    def test_fallback_with_invalid_runtime_schema_field(self):
        # Schema where 'data' is not a dict, so it should be skipped, resulting in empty schema.
        runtime_schema_config = {"data": "not_a_dict"}
        DynamicToolClass = _create_dynamic_crud_tool_class("InvalidSchemaFieldTool", CRUDTool, runtime_schema_config)
        self.assertEqual(DynamicToolClass, CRUDTool) # Fallback due to no valid fields
        self.assertEqual(DynamicToolClass.args_schema, CRUDToolInput)


class TestLoadToolsFromDb(unittest.TestCase):
    def setUp(self):
        # Register mock tools for testing
        self.original_tool_registry = TOOL_REGISTRY.copy()
        TOOL_REGISTRY["CRUDTool"] = CRUDTool # Ensure standard CRUDTool is there
        TOOL_REGISTRY["SampleNonCRUDTool"] = SampleNonCRUDTool

        self.user_id = "test_user"
        self.agent_name = "test_agent"
        self.supabase_url = "http://fake.supabase.co"
        self.supabase_key = "fake_key"

        # Patch os.getenv for Supabase URL and Key for CRUDTool instantiation
        self.patch_os_getenv = patch('os.getenv')
        self.mock_os_getenv = self.patch_os_getenv.start()
        self.mock_os_getenv.side_effect = lambda key, default=None: {
            "SUPABASE_URL": "http://fake.supabase.co",
            "SUPABASE_SERVICE_KEY": "fake_key",
            "GOOGLE_API_KEY": "fake_google_api_key"  # Add this for any Google API calls
        }.get(key, default)
        self.addCleanup(self.patch_os_getenv.stop)

        # Patch create_client used by CRUDTool
        # CRUDTool imports it as: from supabase import create_client
        self.patch_supabase_create_client = patch('supabase.create_client') 
        self.mock_create_supabase_client = self.patch_supabase_create_client.start()
        self.mock_supabase_db_instance = MagicMock()
        self.mock_create_supabase_client.return_value = self.mock_supabase_db_instance
        self.addCleanup(self.patch_supabase_create_client.stop)
        
        # These are passed directly to load_tools_from_db, not via getenv
        self.direct_supabase_url = "http://fake.supabase.co" 
        self.direct_supabase_key = "fake_key"

    def tearDown(self):
        # Restore original TOOL_REGISTRY
        TOOL_REGISTRY.clear()
        TOOL_REGISTRY.update(self.original_tool_registry)

    def test_load_crud_tool_with_dynamic_schema(self):
        tools_data = [
            {
                "name": "CreateItemTool", "description": "Creates an item.", "type": "CRUDTool",
                "config": {
                    "table_name": "items", "method": "create",
                    "runtime_args_schema": {
                        "data": {"type": "dict", "optional": False, "properties": {"name": {"type": "str"}}}
                    }
                }
            }
        ]
        # Pass the direct URL and key, as CRUDTool will use os.getenv for its own init
        loaded_tools = load_tools_from_db(tools_data, self.user_id, self.agent_name, self.direct_supabase_url, self.direct_supabase_key)
        self.assertEqual(len(loaded_tools), 1)
        tool = loaded_tools[0]
        self.assertIsInstance(tool, CRUDTool)
        self.assertEqual(tool.name, "CreateItemTool")
        self.assertEqual(tool.table_name, "items")
        self.assertEqual(tool.method, "create")
        self.assertNotEqual(tool.args_schema, CRUDToolInput) # Dynamic schema was applied
        self.assertIn("data", tool.args_schema.model_fields)
        data_field_type = tool.args_schema.model_fields["data"].annotation
        self.assertIn("name", data_field_type.model_fields)

    def test_load_crud_tool_with_default_schema(self):
        tools_data = [
            {
                "name": "GetItemTool", "description": "Gets an item.", "type": "CRUDTool",
                "config": {"table_name": "items", "method": "read", "runtime_args_schema": {}} # Empty schema
            }
        ]
        loaded_tools = load_tools_from_db(tools_data, self.user_id, self.agent_name, self.direct_supabase_url, self.direct_supabase_key)
        self.assertEqual(len(loaded_tools), 1)
        tool = loaded_tools[0]
        self.assertIsInstance(tool, CRUDTool)
        self.assertEqual(tool.args_schema, CRUDToolInput) # Default schema

    def test_load_non_crud_tool(self):
        tools_data = [
            {
                "name": "MySampleTool", "description": "Does a sample task.", "type": "SampleNonCRUDTool",
                "config": {"custom_config_param": "test_value"}
            }
        ]
        loaded_tools = load_tools_from_db(tools_data, self.user_id, self.agent_name, self.direct_supabase_url, self.direct_supabase_key)
        self.assertEqual(len(loaded_tools), 1)
        tool = loaded_tools[0]
        self.assertIsInstance(tool, SampleNonCRUDTool)
        self.assertEqual(tool.name, "MySampleTool")
        self.assertEqual(tool.custom_config_param, "test_value")
        self.assertEqual(tool.user_id, self.user_id)
        self.assertEqual(tool.agent_name, self.agent_name)

    def test_skip_unregistered_tool(self):
        tools_data = [{"name": "GhostTool", "description": "N/A", "type": "UnknownToolType", "config": {}}]
        loaded_tools = load_tools_from_db(tools_data, self.user_id, self.agent_name, self.direct_supabase_url, self.direct_supabase_key)
        self.assertEqual(len(loaded_tools), 0)

    def test_skip_tool_missing_required_config_for_crud(self):
        tools_data = [
            {"name": "BadCrud", "description": "Bad.", "type": "CRUDTool", "config": {"method": "create"}} # Missing table_name
        ]
        loaded_tools = load_tools_from_db(tools_data, self.user_id, self.agent_name, self.direct_supabase_url, self.direct_supabase_key)
        self.assertEqual(len(loaded_tools), 0)

    def test_skip_tool_missing_name_or_description(self):
        tools_data = [
            {"description": "No name.", "type": "CRUDTool", "config": {"table_name": "t", "method": "c"}},
            {"name": "NoDesc", "type": "CRUDTool", "config": {"table_name": "t", "method": "c"}},
        ]
        loaded_tools = load_tools_from_db(tools_data, self.user_id, self.agent_name, self.direct_supabase_url, self.direct_supabase_key)
        self.assertEqual(len(loaded_tools), 0)


class TestLoadAgentExecutorDb(unittest.TestCase):
    def setUp(self):
        self.patch_create_client = patch('src.core.agent_loader_db.create_client')
        self.mock_supabase_client = self.patch_create_client.start()
        self.db_instance_mock = MagicMock()
        self.mock_supabase_client.return_value = self.db_instance_mock

        self.patch_from_agent_config = patch('src.core.agent_loader_db.CustomizableAgentExecutor.from_agent_config')
        self.mock_from_agent_config = self.patch_from_agent_config.start()
        self.mock_executor = MagicMock(spec=CustomizableAgentExecutor)
        self.mock_from_agent_config.return_value = self.mock_executor

        self.patch_getenv = patch.dict(os.environ, {
            "VITE_SUPABASE_URL": "env_supabase_url",
            "SUPABASE_SERVICE_KEY": "env_supabase_key",
            "GOOGLE_API_KEY": "fake_google_api_key"  # Add this for CustomizableAgentExecutor
        })
        self.patch_getenv.start()
        
        self.agent_name = "DatabaseAgent"
        self.user_id = "db_user"
        self.session_id = "db_session"

        # Mock DB responses
        self.mock_agent_config_data = {
            "id": "agent-uuid-123",
            "agent_name": self.agent_name,
            "llm_config": {"model": "gemini-db", "temperature": 0.1},
            "system_prompt": "You are a DB agent."
        }
        self.mock_tools_data = [] # Default to no tools

        # Setup mock chaining for Supabase client
        mock_agent_response = MagicMock()
        mock_agent_response.data = self.mock_agent_config_data
        self.db_instance_mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_agent_response

        mock_tools_response = MagicMock()
        mock_tools_response.data = self.mock_tools_data # Initially no tools
        # More complex chaining if needed, but direct assignment for now
        # This covers .table("agent_tools").select("*").eq("agent_id", ...).eq("is_active", True).order("order").execute()
        # We might need to make it more specific if table names change or queries become more complex
        self.db_instance_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_tools_response

        # Register SampleNonCRUDTool for tests that might use it
        self.original_tool_registry = TOOL_REGISTRY.copy()
        TOOL_REGISTRY["CRUDTool"] = CRUDTool
        TOOL_REGISTRY["SampleNonCRUDTool"] = SampleNonCRUDTool

    def tearDown(self):
        self.patch_create_client.stop()
        self.patch_from_agent_config.stop()
        self.patch_getenv.stop()
        TOOL_REGISTRY.clear()
        TOOL_REGISTRY.update(self.original_tool_registry)

    def configure_db_responses(self, agent_data, tools_data_list):
        # Agent config response
        agent_resp_mock = MagicMock()
        agent_resp_mock.data = agent_data
        # Tools response
        tools_resp_mock = MagicMock()
        tools_resp_mock.data = tools_data_list

        # This setup assumes the call order or uses different mocks if needed
        # For simplicity, let's assume table('agent_configurations') is called first
        self.db_instance_mock.table.side_effect = lambda table_name: {
            'agent_configurations': MagicMock(
                select=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        single=MagicMock(return_value=MagicMock(
                            execute=MagicMock(return_value=agent_resp_mock)
                        ))
                    ))
                ))
            ),
            'agent_tools': MagicMock(
                select=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            order=MagicMock(return_value=MagicMock(
                                execute=MagicMock(return_value=tools_resp_mock)
                            ))
                        ))
                    ))
                ))
            )
        }[table_name]

    def test_load_executor_success_no_tools(self):
        self.configure_db_responses(self.mock_agent_config_data, []) # No tools
        
        executor = load_agent_executor_db(self.agent_name, self.user_id, self.session_id)
        
        self.assertEqual(executor, self.mock_executor)
        self.mock_supabase_client.assert_called_once_with("env_supabase_url", "env_supabase_key")
        self.mock_from_agent_config.assert_called_once()
        call_kwargs = self.mock_from_agent_config.call_args.kwargs # Get keyword arguments
        agent_config_dict = call_kwargs["agent_config_dict"]
        self.assertEqual(agent_config_dict["agent_name"], self.agent_name)
        self.assertEqual(agent_config_dict["llm"], self.mock_agent_config_data["llm_config"])
        self.assertEqual(agent_config_dict["system_prompt"], self.mock_agent_config_data["system_prompt"])
        
        # Check tools passed to from_agent_config
        passed_tools_list = call_kwargs["tools"]
        self.assertEqual(len(passed_tools_list), 0)

    def test_load_executor_with_crud_tool_dynamic_schema(self):
        crud_tool_db_data = [
            {
                "agent_id": "agent-uuid-123", "name": "DB_CreateItem", "description": "Creates an item in DB.", 
                "type": "CRUDTool", "is_active": True, "order": 1,
                "config": {
                    "table_name": "db_items", "method": "create",
                    "runtime_args_schema": {
                        "data": {"type": "dict", "optional": False, "properties": {"item_name": {"type": "str"}}}
                    }
                }
            }
        ]
        self.configure_db_responses(self.mock_agent_config_data, crud_tool_db_data)
        
        executor = load_agent_executor_db(self.agent_name, self.user_id, self.session_id)
        self.assertEqual(executor, self.mock_executor)
        
        passed_tools_list = self.mock_from_agent_config.call_args.kwargs["tools"]
        self.assertEqual(len(passed_tools_list), 1)
        loaded_tool = passed_tools_list[0]
        self.assertIsInstance(loaded_tool, CRUDTool)
        self.assertEqual(loaded_tool.name, "DB_CreateItem")
        self.assertNotEqual(loaded_tool.args_schema, CRUDToolInput) # Dynamic schema

    def test_load_executor_failure_agent_not_found(self):
        self.configure_db_responses(None, []) # Simulate agent not found
        with self.assertRaisesRegex(ValueError, f"Agent configuration for '{self.agent_name}' not found"):
            load_agent_executor_db(self.agent_name, self.user_id, self.session_id)

    def test_load_executor_failure_missing_supabase_env_vars(self):
        self.patch_getenv.stop() # Stop the patch to remove env vars
        patch.dict(os.environ, clear=True).start() # Clear os.environ for this test case

        with self.assertRaisesRegex(ValueError, "Supabase URL and Service Key must be provided"):
            load_agent_executor_db(self.agent_name, self.user_id, self.session_id)
        
        # Restore for other tests
        patch.dict(os.environ, {
            "VITE_SUPABASE_URL": "env_supabase_url",
            "SUPABASE_SERVICE_KEY": "env_supabase_key"
        }).start() # Start the patch again to restore
        self.patch_getenv.start() # Also restart the original class-level patch if needed


if __name__ == '__main__':
    unittest.main() 