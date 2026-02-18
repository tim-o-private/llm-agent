import logging
import unittest
from typing import Any  # Added Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from langchain.agents import AgentExecutor  # Import AgentExecutor
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
    # return_direct: bool = False # Not needed for this version of BaseTool

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        return "Mock tool response"

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        return "Async mock tool response"

class TestCustomizableAgentExecutorFactory(unittest.TestCase):
    def setUp(self):
        self.mock_llm_instance = MagicMock()
        # Ensure bind_tools returns a mock that can be used in the chain
        self.mock_llm_with_tools = MagicMock()
        self.mock_llm_instance.bind_tools = MagicMock(return_value=self.mock_llm_with_tools)

        # Patch ChatGoogleGenerativeAI where it's imported by the from_agent_config method
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
        self.mock_os_getenv.side_effect = lambda key, default=None: None # No GOOGLE_API_KEY
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
        del self.mock_llm_instance.bind_tools # Simulate LLM without bind_tools
        with self.assertRaisesRegex(AttributeError, "The configured LLM instance does not support .bind_tools()"):
            CustomizableAgentExecutor.from_agent_config(
                self.minimal_config, self.sample_tools, self.user_id, self.session_id
            )

    def test_prompt_templating_with_ltm_and_custom_instructions(self):
        ltm_notes = "Remember this important fact."
        custom_instr = {"task_goal": "Achieve X"}
        config_with_placeholders = {
            "agent_name": "TestAgent",
            "llm": {"model": "gemini-pro", "temperature": 0.5},
            "system_prompt": "Base prompt. {{ltm_notes}} {{custom_instructions}}"
        }
        with patch('src.core.agents.customizable_agent.ChatPromptTemplate.from_messages') as mock_from_messages:
            CustomizableAgentExecutor.from_agent_config(
                config_with_placeholders, self.sample_tools, self.user_id, self.session_id,
                ltm_notes_content=ltm_notes, explicit_custom_instructions_dict=custom_instr
            )
            mock_from_messages.assert_called_once()
            message_templates = mock_from_messages.call_args[0][0]
            system_message_template = None
            for template in message_templates:
                if isinstance(template, tuple) and template[0] == "system":
                    system_message_template = template[1]
                    break
                elif hasattr(template, 'prompt') and hasattr(template.prompt, 'template') and "system" in str(template.role).lower(): # Heuristic for SystemMessagePromptTemplate
                    system_message_template = template.prompt.template
                    break

            self.assertIsNotNone(system_message_template, "System message template not found in prompt")
            self.assertIn("Remember this important fact.", system_message_template)
            self.assertIn("Task Goal: Achieve X", system_message_template)

    def test_prompt_templating_ltm_placeholder_no_content(self):
        config_with_ltm_placeholder = {
            "agent_name": "TestAgent",
            "llm": {"model": "gemini-pro", "temperature": 0.5},
            "system_prompt": "Base prompt. {{ltm_notes}}"
        }
        with patch('src.core.agents.customizable_agent.ChatPromptTemplate.from_messages') as mock_from_messages:
            CustomizableAgentExecutor.from_agent_config(
                config_with_ltm_placeholder, self.sample_tools, self.user_id, self.session_id,
                ltm_notes_content=None
            )
            mock_from_messages.assert_called_once()
            message_templates = mock_from_messages.call_args[0][0]
            system_message_template = None
            for template in message_templates:
                if isinstance(template, tuple) and template[0] == "system":
                    system_message_template = template[1]
                    break
                elif hasattr(template, 'prompt') and hasattr(template.prompt, 'template') and "system" in str(template.role).lower():
                    system_message_template = template.prompt.template
                    break
            self.assertIsNotNone(system_message_template, "System message template not found in prompt")
            self.assertIn("(No LTM notes for this session.)", system_message_template)

    def test_prompt_templating_custom_instr_placeholder_no_content(self):
        config_with_custom_placeholder = {
            "agent_name": "TestAgent",
            "llm": {"model": "gemini-pro", "temperature": 0.5},
            "system_prompt": "Base prompt. {{custom_instructions}}"
        }
        with patch('src.core.agents.customizable_agent.ChatPromptTemplate.from_messages') as mock_from_messages:
            CustomizableAgentExecutor.from_agent_config(
                config_with_custom_placeholder, self.sample_tools, self.user_id, self.session_id,
                explicit_custom_instructions_dict=None
            )
            mock_from_messages.assert_called_once()
            message_templates = mock_from_messages.call_args[0][0]
            system_message_template = None
            for template in message_templates:
                if isinstance(template, tuple) and template[0] == "system":
                    system_message_template = template[1]
                    break
                elif hasattr(template, 'prompt') and hasattr(template.prompt, 'template') and "system" in str(template.role).lower():
                    system_message_template = template.prompt.template
                    break
            self.assertIsNotNone(system_message_template, "System message template not found in prompt")
            self.assertIn("(No explicit custom instructions for this session.)", system_message_template)

class TestUpdateLtmContext(unittest.TestCase):
    """Tests for update_ltm_context — ensures the AgentExecutor interface is preserved.

    Root cause of prior bugs: update_ltm_context assigned self.agent = RunnableSequence,
    bypassing AgentExecutor's Pydantic validator that wraps runnables in RunnableAgent.
    RunnableAgent provides input_keys and aplan(); a raw RunnableSequence does not.
    """

    def setUp(self):
        self.mock_llm_instance = MagicMock()
        self.mock_llm_with_tools = MagicMock()
        self.mock_llm_instance.bind_tools = MagicMock(return_value=self.mock_llm_with_tools)

        self.patch_chat_google = patch('langchain_google_genai.ChatGoogleGenerativeAI', return_value=self.mock_llm_instance)
        self.patch_chat_google.start()
        self.addCleanup(self.patch_chat_google.stop)

        self.patch_os_getenv = patch('os.getenv')
        mock_getenv = self.patch_os_getenv.start()
        mock_getenv.side_effect = lambda key, default=None: {"GOOGLE_API_KEY": "fake"}.get(key, default)
        self.addCleanup(self.patch_os_getenv.stop)

        self.config = {
            "agent_name": "TestAgent",
            "llm": {"model": "gemini-pro", "temperature": 0.0},
            "system_prompt": "You are a test agent.",
        }
        self.executor = CustomizableAgentExecutor.from_agent_config(
            self.config, [], "user-1", "session-1"
        )

    def test_agent_has_aplan_after_init(self):
        """Regression: agent must have aplan after initial construction."""
        self.assertTrue(hasattr(self.executor.agent, 'aplan'),
                        "self.agent must have aplan() — if this fails, AgentExecutor's validator broke")

    def test_agent_has_input_keys_after_init(self):
        """Regression: agent must respond to input_keys after initial construction."""
        self.assertTrue(hasattr(self.executor, 'input_keys'))
        self.assertIn("input", self.executor.input_keys)

    def test_update_ltm_context_preserves_aplan(self):
        """Critical regression: update_ltm_context must not strip aplan from self.agent."""
        self.executor.update_ltm_context("User cares about invoices.")
        self.assertTrue(hasattr(self.executor.agent, 'aplan'),
                        "aplan() missing after update_ltm_context — self.agent was replaced with raw RunnableSequence")

    def test_update_ltm_context_updates_runnable_not_agent_wrapper(self):
        """The agent wrapper (RunnableAgent/RunnableMultiActionAgent) should be reused; only .runnable updated."""
        original_agent_wrapper = self.executor.agent
        self.executor.update_ltm_context("Some notes.")
        # The wrapper object should be the same instance
        self.assertIs(self.executor.agent, original_agent_wrapper,
                      "self.agent wrapper was replaced — should update .runnable instead")
        # But the inner runnable should be replaced
        self.assertIsNotNone(self.executor.agent.runnable)

    def test_update_ltm_context_with_none_is_safe(self):
        """update_ltm_context(None) must not crash and must preserve aplan."""
        self.executor.update_ltm_context(None)
        self.assertTrue(hasattr(self.executor.agent, 'aplan'))

    def test_update_ltm_context_missing_rebuild_state(self):
        """If rebuild state is missing, update_ltm_context logs warning and returns safely."""
        self.executor._base_system_prompt = None
        self.executor._llm_with_tools = None
        # Should not raise
        self.executor.update_ltm_context("Some notes.")
        # aplan still present from original init
        self.assertTrue(hasattr(self.executor.agent, 'aplan'))


class TestCustomizableAgentExecutorInvoke(unittest.IsolatedAsyncioTestCase):
    async def test_ainvoke_adds_empty_chat_history_if_missing(self):
        # Create a proper Runnable agent instead of AsyncMock
        from langchain_core.runnables import RunnableLambda

        def mock_agent_function(inputs):
            return {"output": "test"}

        mock_agent_runnable = RunnableLambda(mock_agent_function)

        # Patching the super().ainvoke to inspect its call
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
        # Create a proper Runnable agent instead of AsyncMock
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


# Test suite for get_customizable_agent_executor (the helper function)
class TestGetCustomizableAgentExecutorHelper(unittest.TestCase):
    def setUp(self):
        self.patch_from_config = patch.object(CustomizableAgentExecutor, 'from_agent_config')
        self.mock_from_config = self.patch_from_config.start()
        self.addCleanup(self.patch_from_config.stop)

        self.agent_config_dict = {"name": "test_agent_dict"}
        self.tools = [MagicMock(spec=BaseTool)]
        self.user_id = "helper_user"
        self.session_id = "helper_session"
        self.ltm = "notes"
        self.custom_instr = {"detail": "high"}

    def test_get_executor_with_dict_config(self):
        get_customizable_agent_executor(
            agent_config_obj=self.agent_config_dict,
            user_id_for_agent=self.user_id,
            session_id_for_agent=self.session_id,
            ltm_notes=self.ltm,
            custom_instructions=self.custom_instr,
            loaded_tools=self.tools
        )
        self.mock_from_config.assert_called_once_with(
            agent_config_dict=self.agent_config_dict,
            tools=self.tools,
            user_id=self.user_id,
            session_id=self.session_id,
            ltm_notes_content=self.ltm,
            explicit_custom_instructions_dict=self.custom_instr,
            logger_instance=None # Default logger was used
        )

    def test_get_executor_with_non_dict_config_logs_error_and_proceeds_if_has_get(self):
        # A mock object that has a 'get' method to simulate a dict-like object
        mock_config_obj_with_get = MagicMock()
        mock_config_obj_with_get.get = MagicMock(return_value="some_value")
        # Setup to behave like a dict for the purpose of from_agent_config if it were to try attribute access
        # This is mostly to check the logging path. The actual success depends on from_agent_config logic.

        with patch.object(logging.getLogger('src.core.agents.customizable_agent'), 'error') as mock_logger_error:
            get_customizable_agent_executor(
                agent_config_obj=mock_config_obj_with_get,
                user_id_for_agent=self.user_id,
                session_id_for_agent=self.session_id,
                ltm_notes=self.ltm,
                custom_instructions=self.custom_instr,
                loaded_tools=self.tools
            )
            mock_logger_error.assert_called_once()
            self.assertIn("received non-dict agent_config_obj", mock_logger_error.call_args[0][0])
            # Check if from_agent_config was still called
            self.mock_from_config.assert_called_once_with(
                agent_config_dict=mock_config_obj_with_get, # Passed through
                tools=self.tools,
                user_id=self.user_id,
                session_id=self.session_id,
                ltm_notes_content=self.ltm,
                explicit_custom_instructions_dict=self.custom_instr,
                logger_instance=None
            )

    def test_get_executor_with_non_dict_config_raises_typeerror_if_not_dict_like(self):
        non_dict_like_obj = object() # Plain object without 'get'
        with self.assertRaisesRegex(TypeError, "agent_config_obj must be a dictionary, got <class 'object'>"):
            get_customizable_agent_executor(
                agent_config_obj=non_dict_like_obj,
                user_id_for_agent=self.user_id,
                session_id_for_agent=self.session_id,
                ltm_notes=self.ltm,
                custom_instructions=self.custom_instr,
                loaded_tools=self.tools
            )

if __name__ == '__main__':
    unittest.main()
