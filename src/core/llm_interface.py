import os
from langchain_core.messages import HumanMessage, SystemMessage
from utils.config_loader import ConfigLoader

class LLMInterface:
    """
    Handles communication with the configured LLM (Claude or Gemini)
    using LangChain.
    """
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.provider = self.config.get('llm.provider', default='gemini').lower()
        self.model_name = self.config.get('llm.model', default='gemini-pro')
        self.temperature = float(self.config.get('llm.temperature', default=0.7))

        if self.provider == 'claude':
            from langchain_anthropic import ChatAnthropic
            self.api_key = os.getenv("ANTHROPIC_API_KEY") or self.config.get('ANTHROPIC_API_KEY')
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not found. Please set it in your .env file.")
            self.llm = ChatAnthropic(
                model=self.model_name,
                anthropic_api_key=self.api_key,
                temperature=self.temperature,
            )
        else:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self.api_key = self.config.get('GOOGLE_API_KEY')
            if not self.api_key:
                raise ValueError("Google API Key not found. Please set GOOGLE_API_KEY in your .env file.")
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=self.temperature,
                convert_system_message_to_human=True
            )

    def generate_text(self, prompt: str, system_context: str = "") -> str:
        """
        Generates text using the LLM based on a prompt and optional system context.

        Args:
            prompt: The user's query or instruction.
            system_context: Optional system-level instructions or context.

        Returns:
            The LLM's generated text response.

        Raises:
            Exception: If the LLM API call fails.
        """
        messages = []
        if system_context:
            messages.append(SystemMessage(content=system_context))
        messages.append(HumanMessage(content=prompt))

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            raise
