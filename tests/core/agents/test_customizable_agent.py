import logging
import unittest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from langchain.agents import AgentExecutor
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool

# Module to test
from src.core.agents.customizable_agent import (
    CustomizableAgentExecutor,
    get_customizable_agent_executor,
    preprocess_intermediate_steps,
)

# Basic logger for tests
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TestPreprocessIntermediateSteps(unittest.TestCase):
    def test_empty_observation(self):
        steps = [(MagicMock(name="action1"), "")]
        processed = preprocess_intermediate_steps(steps)
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0][1], "(Tool returned no output or an empty string)")

    def test_none_observation(self):
        steps = [(MagicMock(name="action1"), None)]
        processed = preprocess_intermediate_steps(steps)
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0][1], "(Tool returned no output or an empty string)")

    def test_valid_observation(self):
        steps = [(MagicMock(name="action1"), "Valid output")]
        processed = preprocess_intermediate_steps(steps)
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0][1], "Valid output")

    def test_mixed_observations(self):
        steps = [
            (MagicMock(name="action1"), "Output1"),
            (MagicMock(name="action2"), None),
            (MagicMock(name="action3"), ""),
            (MagicMock(name="action4"), "Output4")
        ]
        processed = preprocess_intermediate_steps(steps)
        self.assertEqual(len(processed), 4)
        self.assertEqual(processed[0][1], "Output1")
        self.assertEqual(processed[1][1], "(Tool returned no output or an empty string)")
        self.assertEqual(processed[2][1], "(Tool returned no output or an empty string)")
        self.assertEqual(processed[3][1], "Output4")

    def test_no_steps(self):
        steps = []
        processed = preprocess_intermediate_steps(steps)
        self.assertEqual(len(processed), 0)

# Mock Tool for testing
class MockTool(BaseTool):
    name: str = "mock_tool"
    description: str = "A mock tool"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        return "Mock tool response"

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        return "Async mock tool response"

class TestCustomizableAgentExecutorFactory(unittest.TestCase):
    def setUp(self):
        self.mock_llm_instance = MagicMock()
        self.mock_llm_with_tools = MagicMock()
        self.mock_llm_instance.bind_tools = MagicMock(return_value=self.mock_llm_with_tools)

        self.patch_chat_google = patch('langchain_google_genai.ChatGoogleGenerativeAI', return_value=self.mock_llm_instance)
        self.mock_chat_google_class = self.patch_chat_google.start()
        self.addCleanup(self.patch_chat_google.stop)

        self.patch_os_getenv = patch('os.getenv')
        self.mock_os_getenv = self.patch_os_getenv.start()
        self.mock_os_getenv.side_effect = lambda key, default=None: {
            "GOOGLE_API_KEY": "fake_google_api_key"
        }.get(key, default)
        self.addCleanup(self.patch_os_getenv.stop)

        self.sample_tools = [MagicMock(spec=BaseTool)]
        self.user_id = "test_user"
        self.session_id = "test_session"
        self.minimal_config = {
            "agent_name": "TestAgent",
            "llm": {"model": "gemini-pro", "temperature": 0.5},
            "system_prompt": "You are a test agent."
        }

    def test_creation_success_minimal(self):
        executor = CustomizableAgentExecutor.from_agent_config(
            self.minimal_config, self.sample_tools, self.user_id, self.session_id
        )
        self.assertIsInstance(executor, CustomizableAgentExecutor)
        self.mock_chat_google_class.assert_called_once_with(
            model="gemini-pro",
            google_api_key="fake_google_api_key",
            temperature=0.5
        )
        self.mock_llm_instance.bind_tools.assert_called_once_with(self.sample_tools)

    def test_creation_missing_google_api_key(self):
        self.mock_os_getenv.side_effect = lambda key, default=None: None
        with self.assertRaisesRegex(ValueError, "GOOGLE_API_KEY not found for ChatGoogleGenerativeAI."):
            CustomizableAgentExecutor.from_agent_config(
                self.minimal_config, self.sample_tools, self.user_id, self.session_id
            )

    def test_creation_missing_llm_model_config(self):
        bad_config = self.minimal_config.copy()
        del bad_config["llm"]
        with self.assertRaisesRegex(ValueError, "LLM model configuration is missing or incomplete"):
            CustomizableAgentExecutor.from_agent_config(
                bad_config, self.sample_tools, self.user_id, self.session_id
            )

        bad_config_no_model = {"agent_name": "Test", "llm": {"temperature": 0.5}, "system_prompt": "Test"}
        with self.assertRaisesRegex(ValueError, "LLM model configuration is missing or incomplete"):
            CustomizableAgentExecutor.from_agent_config(
                bad_config_no_model, self.sample_tools, self.user_id, self.session_id
            )

    def test_creation_missing_system_prompt(self):
        bad_config = self.minimal_config.copy()
        del bad_config["system_prompt"]
        with self.assertRaisesRegex(ValueError, "'system_prompt' is missing"):
            CustomizableAgentExecutor.from_agent_config(
                bad_config, self.sample_tools, self.user_id, self.session_id
            )

    def test_creation_llm_lacks_bind_tools(self):
        del self.mock_llm_instance.bind_tools
        with self.assertRaisesRegex(AttributeError, "The configured LLM instance does not support .bind_tools()"):
            CustomizableAgentExecutor.from_agent_config(
                self.minimal_config, self.sample_tools, self.user_id, self.session_id
            )

    def test_system_prompt_passed_directly_to_template(self):
        """Verify the assembled prompt string is used directly (no LTM/custom instructions processing)."""
        assembled_prompt = "## Soul\nBe helpful.\n\n## Channel\nweb\n\n## Memory\nUse read_memory."
        config = {
            "agent_name": "TestAgent",
            "llm": {"model": "gemini-pro", "temperature": 0.5},
            "system_prompt": assembled_prompt,
        }
        with patch('src.core.agents.customizable_agent.ChatPromptTemplate.from_messages') as mock_from_messages:
            CustomizableAgentExecutor.from_agent_config(
                config, self.sample_tools, self.user_id, self.session_id
            )
            mock_from_messages.assert_called_once()
            message_templates = mock_from_messages.call_args[0][0]
            system_message_template = None
            for template in message_templates:
                if isinstance(template, tuple) and template[0] == "system":
                    system_message_template = template[1]
                    break
            self.assertIsNotNone(system_message_template)
            self.assertEqual(system_message_template, assembled_prompt)

    def test_no_build_system_message_method(self):
        """Verify _build_system_message has been removed."""
        self.assertFalse(hasattr(CustomizableAgentExecutor, '_build_system_message'))

    def test_no_update_ltm_context_method(self):
        """Verify update_ltm_context has been removed."""
        executor = CustomizableAgentExecutor.from_agent_config(
            self.minimal_config, self.sample_tools, self.user_id, self.session_id
        )
        self.assertFalse(hasattr(executor, 'update_ltm_context'))

    def test_no_base_system_prompt_field(self):
        """Verify _base_system_prompt field has been removed."""
        executor = CustomizableAgentExecutor.from_agent_config(
            self.minimal_config, self.sample_tools, self.user_id, self.session_id
        )
        self.assertFalse(hasattr(executor, '_base_system_prompt'))


class TestCustomizableAgentExecutorInvoke(unittest.IsolatedAsyncioTestCase):
    async def test_ainvoke_adds_empty_chat_history_if_missing(self):
        from langchain_core.runnables import RunnableLambda

        def mock_agent_function(inputs):
            return {"output": "test"}

        mock_agent_runnable = RunnableLambda(mock_agent_function)

        with patch.object(AgentExecutor, 'ainvoke', new_callable=AsyncMock) as mock_super_ainvoke:
            mock_super_ainvoke.return_value = {"output": "super_called"}

            mock_executor = CustomizableAgentExecutor(agent=mock_agent_runnable, tools=[])

            input_dict = {"input": "hello"}
            await mock_executor.ainvoke(input_dict)

            mock_super_ainvoke.assert_called_once()
            called_input = mock_super_ainvoke.call_args[0][0]
            self.assertIn("chat_history", called_input)
            self.assertEqual(called_input["chat_history"], [])

    async def test_ainvoke_uses_provided_chat_history(self):
        from langchain_core.runnables import RunnableLambda

        def mock_agent_function(inputs):
            return {"output": "test"}

        mock_agent_runnable = RunnableLambda(mock_agent_function)

        existing_history = [HumanMessage(content="Hi there")]

        with patch.object(AgentExecutor, 'ainvoke', new_callable=AsyncMock) as mock_super_ainvoke:
            mock_super_ainvoke.return_value = {"output": "super_called"}

            mock_executor = CustomizableAgentExecutor(agent=mock_agent_runnable, tools=[])

            input_dict = {"input": "hello again", "chat_history": existing_history}
            await mock_executor.ainvoke(input_dict)

            mock_super_ainvoke.assert_called_once()
            called_input = mock_super_ainvoke.call_args[0][0]
            self.assertEqual(called_input["chat_history"], existing_history)


class TestGetCustomizableAgentExecutorHelper(unittest.TestCase):
    def setUp(self):
        self.patch_from_config = patch.object(CustomizableAgentExecutor, 'from_agent_config')
        self.mock_from_config = self.patch_from_config.start()
        self.addCleanup(self.patch_from_config.stop)

        self.agent_config_dict = {"name": "test_agent_dict", "system_prompt": "test", "llm": {"model": "test"}}
        self.tools = [MagicMock(spec=BaseTool)]
        self.user_id = "helper_user"
        self.session_id = "helper_session"

    def test_get_executor_with_dict_config(self):
        get_customizable_agent_executor(
            agent_config_obj=self.agent_config_dict,
            user_id_for_agent=self.user_id,
            session_id_for_agent=self.session_id,
            loaded_tools=self.tools
        )
        self.mock_from_config.assert_called_once_with(
            agent_config_dict=self.agent_config_dict,
            tools=self.tools,
            user_id=self.user_id,
            session_id=self.session_id,
            logger_instance=None
        )

    def test_get_executor_with_non_dict_config_logs_error_and_proceeds_if_has_get(self):
        mock_config_obj_with_get = MagicMock()
        mock_config_obj_with_get.get = MagicMock(return_value="some_value")

        with patch.object(logging.getLogger('src.core.agents.customizable_agent'), 'error') as mock_logger_error:
            get_customizable_agent_executor(
                agent_config_obj=mock_config_obj_with_get,
                user_id_for_agent=self.user_id,
                session_id_for_agent=self.session_id,
                loaded_tools=self.tools
            )
            mock_logger_error.assert_called_once()
            self.assertIn("received non-dict agent_config_obj", mock_logger_error.call_args[0][0])
            self.mock_from_config.assert_called_once_with(
                agent_config_dict=mock_config_obj_with_get,
                tools=self.tools,
                user_id=self.user_id,
                session_id=self.session_id,
                logger_instance=None
            )

    def test_get_executor_with_non_dict_config_raises_typeerror_if_not_dict_like(self):
        non_dict_like_obj = object()
        with self.assertRaisesRegex(TypeError, "agent_config_obj must be a dictionary, got <class 'object'>"):
            get_customizable_agent_executor(
                agent_config_obj=non_dict_like_obj,
                user_id_for_agent=self.user_id,
                session_id_for_agent=self.session_id,
                loaded_tools=self.tools
            )

if __name__ == '__main__':
    unittest.main()
