import logging
import os
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from core.tools.crud_tool import CRUDTool, CRUDToolInput

# Modules to test
from src.core.agent_loader_db import (
    TOOL_REGISTRY,
    _create_dynamic_args_model,
    _create_dynamic_crud_tool_class,
    _fetch_user_instructions,
    load_agent_executor_db,
    load_tools_from_db,
)
from src.core.agents.customizable_agent import CustomizableAgentExecutor

# Basic logger for tests
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

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
        self.assertTrue(issubclass(DynamicModel, BaseModel))
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
        self.assertNotEqual(DynamicToolClass, CRUDTool)
        self.assertTrue(hasattr(DynamicToolClass, 'args_schema'))
        self.assertNotEqual(DynamicToolClass.args_schema, CRUDToolInput)

        args_schema = DynamicToolClass.args_schema
        self.assertIn("data", args_schema.model_fields)
        self.assertTrue(args_schema.model_fields["data"].is_required())
        data_field_type = args_schema.model_fields["data"].annotation
        self.assertTrue(issubclass(data_field_type, BaseModel))
        self.assertIn("item_name", data_field_type.model_fields)
        self.assertEqual(data_field_type.model_fields["item_name"].annotation, str)

        self.assertIn("filters", args_schema.model_fields)
        self.assertFalse(args_schema.model_fields["filters"].is_required())
        filters_field_type = args_schema.model_fields["filters"].annotation
        self.assertTrue(issubclass(filters_field_type.__args__[0], BaseModel) if hasattr(filters_field_type, '__args__') else issubclass(filters_field_type, BaseModel))
        actual_filter_model = filters_field_type.__args__[0] if hasattr(filters_field_type, '__args__') else filters_field_type
        self.assertIn("filter_id", actual_filter_model.model_fields)

    def test_fallback_to_base_schema_if_config_empty(self):
        DynamicToolClass = _create_dynamic_crud_tool_class("EmptySchemaTool", CRUDTool, {})
        self.assertEqual(DynamicToolClass, CRUDTool)
        self.assertEqual(DynamicToolClass.args_schema, CRUDToolInput)

    def test_fallback_with_invalid_runtime_schema_field(self):
        runtime_schema_config = {"data": "not_a_dict"}
        DynamicToolClass = _create_dynamic_crud_tool_class("InvalidSchemaFieldTool", CRUDTool, runtime_schema_config)
        self.assertEqual(DynamicToolClass, CRUDTool)
        self.assertEqual(DynamicToolClass.args_schema, CRUDToolInput)


class TestLoadToolsFromDb(unittest.TestCase):
    def setUp(self):
        self.original_tool_registry = TOOL_REGISTRY.copy()
        TOOL_REGISTRY["CRUDTool"] = CRUDTool
        TOOL_REGISTRY["SampleNonCRUDTool"] = SampleNonCRUDTool

        self.user_id = "test_user"
        self.agent_name = "test_agent"
        self.supabase_url = "http://fake.supabase.co"
        self.supabase_key = "fake_key"

        self.patch_os_getenv = patch('os.getenv')
        self.mock_os_getenv = self.patch_os_getenv.start()
        self.mock_os_getenv.side_effect = lambda key, default=None: {
            "SUPABASE_URL": "http://fake.supabase.co",
            "SUPABASE_SERVICE_KEY": "fake_key",
            "GOOGLE_API_KEY": "fake_google_api_key"
        }.get(key, default)
        self.addCleanup(self.patch_os_getenv.stop)

        self.patch_supabase_create_client = patch('supabase.create_client')
        self.mock_create_supabase_client = self.patch_supabase_create_client.start()
        self.mock_supabase_db_instance = MagicMock()
        self.mock_create_supabase_client.return_value = self.mock_supabase_db_instance
        self.addCleanup(self.patch_supabase_create_client.stop)

        self.direct_supabase_url = "http://fake.supabase.co"
        self.direct_supabase_key = "fake_key"

    def tearDown(self):
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
        loaded_tools = load_tools_from_db(tools_data, self.user_id, self.agent_name, self.direct_supabase_url, self.direct_supabase_key)
        self.assertEqual(len(loaded_tools), 1)
        tool = loaded_tools[0]
        self.assertIsInstance(tool, CRUDTool)
        self.assertEqual(tool.name, "CreateItemTool")
        self.assertEqual(tool.table_name, "items")
        self.assertEqual(tool.method, "create")
        self.assertNotEqual(tool.args_schema, CRUDToolInput)
        self.assertIn("data", tool.args_schema.model_fields)
        data_field_type = tool.args_schema.model_fields["data"].annotation
        self.assertIn("name", data_field_type.model_fields)

    def test_load_crud_tool_with_default_schema(self):
        tools_data = [
            {
                "name": "GetItemTool", "description": "Gets an item.", "type": "CRUDTool",
                "config": {"table_name": "items", "method": "read", "runtime_args_schema": {}}
            }
        ]
        loaded_tools = load_tools_from_db(tools_data, self.user_id, self.agent_name, self.direct_supabase_url, self.direct_supabase_key)
        self.assertEqual(len(loaded_tools), 1)
        tool = loaded_tools[0]
        self.assertIsInstance(tool, CRUDTool)
        self.assertEqual(tool.args_schema, CRUDToolInput)

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
            {"name": "BadCrud", "description": "Bad.", "type": "CRUDTool", "config": {"method": "create"}}
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


class TestFetchUserInstructions(unittest.TestCase):
    """Tests for _fetch_user_instructions helper."""

    def test_returns_instructions_when_found(self):
        db = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = {"instructions": "Always use bullet points."}
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_resp

        result = _fetch_user_instructions(db, "user-1", "assistant")
        self.assertEqual(result, "Always use bullet points.")

    def test_returns_none_when_no_row(self):
        db = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = None
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_resp

        result = _fetch_user_instructions(db, "user-1", "assistant")
        self.assertIsNone(result)

    def test_returns_none_when_empty_instructions(self):
        db = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = {"instructions": ""}
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_resp

        result = _fetch_user_instructions(db, "user-1", "assistant")
        self.assertIsNone(result)

    def test_returns_none_on_error(self):
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.side_effect = Exception("DB error")

        result = _fetch_user_instructions(db, "user-1", "assistant")
        self.assertIsNone(result)


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

        self.patch_build_prompt = patch('chatServer.services.prompt_builder.build_agent_prompt')
        self.mock_build_prompt = self.patch_build_prompt.start()
        self.mock_build_prompt.return_value = "## Soul\nYou are a test agent.\n\n## Channel\nweb"

        self.patch_getenv = patch.dict(os.environ, {
            "VITE_SUPABASE_URL": "env_supabase_url",
            "SUPABASE_SERVICE_KEY": "env_supabase_key",
            "GOOGLE_API_KEY": "fake_google_api_key"
        })
        self.patch_getenv.start()

        self.agent_name = "DatabaseAgent"
        self.user_id = "db_user"
        self.session_id = "db_session"

        # Mock DB responses - note: column is now 'soul' not 'system_prompt'
        self.mock_agent_config_data = {
            "id": "agent-uuid-123",
            "agent_name": self.agent_name,
            "llm_config": {"model": "gemini-db", "temperature": 0.1},
            "soul": "You are a DB agent.",
            "identity": {"name": "DBBot", "description": "a database assistant"},
        }
        self.mock_tools_data = []

        mock_agent_response = MagicMock()
        mock_agent_response.data = self.mock_agent_config_data
        self.db_instance_mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_agent_response

        mock_tools_response = MagicMock()
        mock_tools_response.data = self.mock_tools_data
        self.db_instance_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_tools_response

        # Mock user instructions fetch
        mock_instructions_resp = MagicMock()
        mock_instructions_resp.data = None
        self.db_instance_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_instructions_resp

        self.original_tool_registry = TOOL_REGISTRY.copy()
        TOOL_REGISTRY["CRUDTool"] = CRUDTool
        TOOL_REGISTRY["SampleNonCRUDTool"] = SampleNonCRUDTool

    def tearDown(self):
        self.patch_create_client.stop()
        self.patch_from_agent_config.stop()
        self.patch_build_prompt.stop()
        self.patch_getenv.stop()
        TOOL_REGISTRY.clear()
        TOOL_REGISTRY.update(self.original_tool_registry)

    def configure_db_responses(self, agent_data, tools_data_list):
        """Configure mock Supabase responses for agent loading."""
        agent_resp_mock = MagicMock()
        agent_resp_mock.data = agent_data

        assignments = []
        tool_records = {}
        for i, tool in enumerate(tools_data_list or []):
            tool_id = f"tool-uuid-{i}"
            assignments.append({
                "id": f"assignment-uuid-{i}",
                "agent_id": tool.get("agent_id", "agent-uuid-123"),
                "tool_id": tool_id,
                "config_override": {},
                "is_active": True,
                "is_deleted": False,
            })
            tool_records[tool_id] = {
                "id": tool_id,
                "name": tool["name"],
                "type": tool.get("type", "CRUDTool"),
                "description": tool.get("description", ""),
                "config": tool.get("config", {}),
                "is_active": True,
                "is_deleted": False,
            }

        assignments_resp_mock = MagicMock()
        assignments_resp_mock.data = assignments

        # Mock user instructions response
        instructions_resp_mock = MagicMock()
        instructions_resp_mock.data = None

        def make_table_mock(table_name):
            if table_name == 'agent_configurations':
                return MagicMock(
                    select=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            single=MagicMock(return_value=MagicMock(
                                execute=MagicMock(return_value=agent_resp_mock)
                            ))
                        ))
                    ))
                )
            elif table_name == 'agent_tools':
                chain = MagicMock()
                chain.select.return_value = chain
                chain.eq.return_value = chain
                chain.execute.return_value = assignments_resp_mock
                return chain
            elif table_name == 'tools':
                def make_tool_chain():
                    tool_chain = MagicMock()
                    captured_tool_id = [None]

                    def eq_handler(field, value):
                        if field == "id":
                            captured_tool_id[0] = value
                        return tool_chain

                    tool_chain.select.return_value = tool_chain
                    tool_chain.eq.side_effect = eq_handler
                    tool_chain.single.return_value = tool_chain

                    def execute_handler():
                        resp = MagicMock()
                        resp.data = tool_records.get(captured_tool_id[0])
                        return resp

                    tool_chain.execute.side_effect = execute_handler
                    return tool_chain

                return make_tool_chain()
            elif table_name == 'user_agent_prompt_customizations':
                chain = MagicMock()
                chain.select.return_value = chain
                chain.eq.return_value = chain
                chain.maybe_single.return_value = chain
                chain.execute.return_value = instructions_resp_mock
                return chain
            else:
                return MagicMock()

        self.db_instance_mock.table.side_effect = make_table_mock

    def test_load_executor_success_no_tools(self):
        self.configure_db_responses(self.mock_agent_config_data, [])

        executor = load_agent_executor_db(self.agent_name, self.user_id, self.session_id, use_cache=False)

        self.assertEqual(executor, self.mock_executor)
        self.mock_supabase_client.assert_called_once_with("env_supabase_url", "env_supabase_key")
        self.mock_from_agent_config.assert_called_once()
        call_kwargs = self.mock_from_agent_config.call_args.kwargs
        agent_config_dict = call_kwargs["agent_config_dict"]
        self.assertEqual(agent_config_dict["agent_name"], self.agent_name)
        self.assertEqual(agent_config_dict["llm"], self.mock_agent_config_data["llm_config"])
        # system_prompt is now assembled by build_agent_prompt
        self.assertEqual(agent_config_dict["system_prompt"], self.mock_build_prompt.return_value)

        passed_tools_list = call_kwargs["tools"]
        self.assertEqual(len(passed_tools_list), 0)

    def test_load_executor_passes_channel_to_prompt_builder(self):
        self.configure_db_responses(self.mock_agent_config_data, [])

        load_agent_executor_db(self.agent_name, self.user_id, self.session_id, channel="telegram", use_cache=False)

        # Verify build_agent_prompt was called with correct channel
        self.mock_build_prompt.assert_called_once()
        call_kwargs = self.mock_build_prompt.call_args.kwargs
        self.assertEqual(call_kwargs["channel"], "telegram")
        self.assertEqual(call_kwargs["soul"], "You are a DB agent.")
        self.assertEqual(call_kwargs["identity"], {"name": "DBBot", "description": "a database assistant"})

    def test_load_executor_default_channel_is_web(self):
        self.configure_db_responses(self.mock_agent_config_data, [])

        load_agent_executor_db(self.agent_name, self.user_id, self.session_id, use_cache=False)

        call_kwargs = self.mock_build_prompt.call_args.kwargs
        self.assertEqual(call_kwargs["channel"], "web")

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

        executor = load_agent_executor_db(self.agent_name, self.user_id, self.session_id, use_cache=False)
        self.assertEqual(executor, self.mock_executor)

        passed_tools_list = self.mock_from_agent_config.call_args.kwargs["tools"]
        self.assertEqual(len(passed_tools_list), 1)
        loaded_tool = passed_tools_list[0]
        self.assertIsInstance(loaded_tool, CRUDTool)
        self.assertEqual(loaded_tool.name, "DB_CreateItem")
        self.assertNotEqual(loaded_tool.args_schema, CRUDToolInput)

    def test_load_executor_failure_agent_not_found(self):
        self.configure_db_responses(None, [])
        with self.assertRaisesRegex(ValueError, f"Agent configuration for '{self.agent_name}' not found"):
            load_agent_executor_db(self.agent_name, self.user_id, self.session_id, use_cache=False)

    def test_load_executor_failure_missing_supabase_env_vars(self):
        self.patch_getenv.stop()
        patch.dict(os.environ, clear=True).start()

        with self.assertRaisesRegex(ValueError, "Supabase URL and Service Key must be provided"):
            load_agent_executor_db(self.agent_name, self.user_id, self.session_id, use_cache=False)

        patch.dict(os.environ, {
            "VITE_SUPABASE_URL": "env_supabase_url",
            "SUPABASE_SERVICE_KEY": "env_supabase_key"
        }).start()
        self.patch_getenv.start()

    def test_load_executor_does_not_pass_ltm_to_from_agent_config(self):
        """Verify LTM is no longer passed to from_agent_config."""
        self.configure_db_responses(self.mock_agent_config_data, [])

        load_agent_executor_db(self.agent_name, self.user_id, self.session_id, use_cache=False)

        call_kwargs = self.mock_from_agent_config.call_args.kwargs
        # ltm_notes_content should NOT be in the kwargs
        self.assertNotIn("ltm_notes_content", call_kwargs)
        # explicit_custom_instructions_dict should NOT be in the kwargs
        self.assertNotIn("explicit_custom_instructions_dict", call_kwargs)


if __name__ == '__main__':
    unittest.main()
