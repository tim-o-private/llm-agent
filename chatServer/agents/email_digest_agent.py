"""Email Digest Agent using existing agent framework."""
# @docs memory-bank/patterns/agent-patterns.md#pattern-5-agent-configuration-pattern
# @rules memory-bank/rules/agent-rules.json#agent-003

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from ..tools.gmail_tools import GmailDigestTool, GmailSearchTool
    from ..config.constants import DEFAULT_LOG_LEVEL
except ImportError:
    from chatServer.tools.gmail_tools import GmailDigestTool, GmailSearchTool
    from chatServer.config.constants import DEFAULT_LOG_LEVEL

# Import existing agent framework
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

try:
    from core.agents.customizable_agent import CustomizableAgentExecutor
    from core.llm_interface import LLMInterface
    from utils.config_loader import ConfigLoader
    from utils.logging_utils import get_logger
except ImportError:
    # Fallback for when running from different context
    from src.core.agents.customizable_agent import CustomizableAgentExecutor
    from src.core.llm_interface import LLMInterface
    from src.utils.config_loader import ConfigLoader
    from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class EmailDigestAgent:
    """Agent specialized for email digest generation and management."""
    
    def __init__(self, user_id: str, session_id: str, config_loader: Optional[ConfigLoader] = None):
        """Initialize Email Digest Agent.
        
        Args:
            user_id: User ID for scoping
            session_id: Session ID for memory
            config_loader: Optional config loader instance
        """
        self.user_id = user_id
        self.session_id = session_id
        self.agent_name = "email_digest_agent"
        
        # Initialize configuration
        self.config = config_loader or ConfigLoader()
        
        # Initialize tools
        self.tools = self._create_tools()
        
        # Agent configuration for email digest tasks
        self.agent_config = {
            "name": self.agent_name,
            "description": "Specialized agent for email digest generation and email management tasks",
            "model": "gemini-pro",  # Use existing model configuration
            "system_prompt": self._get_system_prompt(),
            "tools": self.tools,
            "memory_config": {
                "type": "postgresql",
                "table_name": "chat_history"
            }
        }
        
        # Create agent executor
        self.executor = None
    
    def _create_tools(self) -> List:
        """Create Gmail tools for the agent."""
        tools = []
        
        try:
            # Gmail digest tool
            gmail_digest_tool = GmailDigestTool(
                user_id=self.user_id,
                gmail_credentials_path=None,  # Will use default paths
                gmail_token_path=None
            )
            tools.append(gmail_digest_tool)
            
            # Gmail search tool
            gmail_search_tool = GmailSearchTool(
                user_id=self.user_id,
                gmail_credentials_path=None,
                gmail_token_path=None
            )
            tools.append(gmail_search_tool)
            
            logger.info(f"Created {len(tools)} Gmail tools for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to create Gmail tools: {e}")
            # Continue without Gmail tools - agent can still provide general assistance
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for email digest agent."""
        return """You are an Email Digest Agent, specialized in helping users manage and understand their email communications.

Your primary capabilities include:
1. **Email Digest Generation**: Create summaries of recent emails, highlighting important messages and key information
2. **Email Search**: Help users find specific emails using Gmail search syntax
3. **Email Analysis**: Analyze email patterns, identify important senders, and categorize messages
4. **Email Management Advice**: Provide suggestions for email organization and productivity

When generating email digests:
- Focus on actionable items and important information
- Highlight urgent or time-sensitive emails
- Group related emails by thread or topic
- Provide clear, concise summaries
- Identify emails that require responses

When searching emails:
- Use appropriate Gmail search syntax (e.g., 'is:unread', 'from:sender@example.com', 'newer_than:2d')
- Explain search results clearly
- Suggest follow-up actions when relevant

Always prioritize user privacy and security. Only access emails when explicitly requested and for legitimate purposes.

If Gmail tools are not available, explain the limitation and offer alternative assistance."""
    
    async def get_agent_executor(self) -> CustomizableAgentExecutor:
        """Get or create agent executor using existing framework."""
        if self.executor is None:
            try:
                # Use existing agent framework
                self.executor = CustomizableAgentExecutor.from_agent_config(
                    agent_config_dict=self.agent_config,
                    tools=self.tools,
                    user_id=self.user_id,
                    session_id=self.session_id,
                    logger_instance=logger
                )
                logger.info(f"Created email digest agent executor for user {self.user_id}")
                
            except Exception as e:
                logger.error(f"Failed to create agent executor: {e}")
                raise RuntimeError(f"Failed to initialize email digest agent: {e}")
        
        return self.executor
    
    async def generate_digest(self, hours_back: int = 24, max_threads: int = 20, include_read: bool = False) -> str:
        """Generate email digest using the agent.
        
        Args:
            hours_back: Hours to look back for emails
            max_threads: Maximum number of threads to analyze
            include_read: Whether to include read emails
            
        Returns:
            Email digest summary
        """
        try:
            executor = await self.get_agent_executor()
            
            # Create input for the agent
            user_input = (
                f"Generate an email digest for the last {hours_back} hours. "
                f"Analyze up to {max_threads} email threads. "
                f"{'Include' if include_read else 'Exclude'} read emails. "
                f"Focus on important messages and actionable items."
            )
            
            # Invoke the agent
            response = await executor.ainvoke({
                "input": user_input,
                "chat_history": []  # Fresh context for digest generation
            })
            
            return response.get("output", "Failed to generate email digest")
            
        except Exception as e:
            logger.error(f"Error generating email digest: {e}")
            return f"Failed to generate email digest: {e}"
    
    async def search_emails(self, query: str, max_results: int = 20) -> str:
        """Search emails using the agent.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            Search results summary
        """
        try:
            executor = await self.get_agent_executor()
            
            user_input = (
                f"Search my Gmail for: {query}. "
                f"Show up to {max_results} results. "
                f"Provide a clear summary of the search results."
            )
            
            response = await executor.ainvoke({
                "input": user_input,
                "chat_history": []
            })
            
            return response.get("output", "Failed to search emails")
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return f"Failed to search emails: {e}"
    
    async def analyze_emails(self, analysis_request: str) -> str:
        """Perform custom email analysis using the agent.
        
        Args:
            analysis_request: Description of the analysis to perform
            
        Returns:
            Analysis results
        """
        try:
            executor = await self.get_agent_executor()
            
            user_input = f"Analyze my emails: {analysis_request}"
            
            response = await executor.ainvoke({
                "input": user_input,
                "chat_history": []
            })
            
            return response.get("output", "Failed to analyze emails")
            
        except Exception as e:
            logger.error(f"Error analyzing emails: {e}")
            return f"Failed to analyze emails: {e}"
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent."""
        return {
            "agent_name": self.agent_name,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tools_count": len(self.tools),
            "tools": [tool.name for tool in self.tools],
            "capabilities": [
                "Email digest generation",
                "Email search",
                "Email analysis",
                "Email management advice"
            ],
            "status": "ready" if self.tools else "limited (no Gmail access)"
        } 