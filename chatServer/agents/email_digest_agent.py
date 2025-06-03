"""Email Digest Agent using existing agent framework."""
# @docs memory-bank/patterns/agent-patterns.md#pattern-5-agent-configuration-pattern
# @rules memory-bank/rules/agent-rules.json#agent-003

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

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

try:
    from ..database.connection import get_db_connection
    from ..config.constants import DEFAULT_LOG_LEVEL
except ImportError:
    from chatServer.database.connection import get_db_connection
    from chatServer.config.constants import DEFAULT_LOG_LEVEL

# Import Gmail tools
try:
    from ..tools.gmail_tools import GmailDigestTool, GmailSearchTool
except ImportError:
    try:
        from chatServer.tools.gmail_tools import GmailDigestTool, GmailSearchTool
    except ImportError:
        # Handle case where Gmail tools are not available
        GmailDigestTool = None
        GmailSearchTool = None

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
        
        # Agent configuration that tests expect
        self.agent_config = {
            "name": self.agent_name,
            "system_prompt": self._get_system_prompt(),
            "llm": {
                "model": "gemini-pro",
                "temperature": 0.1
            },
            "capabilities": [
                "Email digest generation",
                "Email search",
                "Email analysis",
                "Email management advice"
            ]
        }
        
        # Initialize tools
        self.tools = self._create_tools()
        
        # Agent executor will be created on demand
        self.executor = None
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the email digest agent."""
        return """You are an Email Digest Agent specialized in email management and digest generation. Your primary role is to help users understand and manage their email communications effectively.

Key responsibilities:
1. Email Digest Generation - Create comprehensive summaries of recent messages
2. Email Search - Find specific emails using Gmail search syntax
3. Email Analysis - Identify patterns and important communications
4. Email Management - Provide actionable advice for email organization

When generating email digests:
- Focus on actionable items and important communications
- Group related emails together when possible
- Highlight urgent or time-sensitive messages
- Provide clear subject lines and sender information
- Summarize key points without losing important details

When searching emails:
- Use appropriate Gmail search syntax (is:unread, from:, subject:, etc.)
- Respect user-specified time ranges and filters
- Return relevant results with clear context

Always maintain a professional, helpful tone and respect user privacy and security.
"""
    
    def _create_tools(self) -> List[Any]:
        """Create Gmail tools for the agent."""
        tools = []
        
        try:
            if GmailDigestTool is not None:
                # Create Gmail digest tool
                digest_tool = GmailDigestTool(
                    user_id=self.user_id,
                    name="gmail_digest",
                    description="Generate a digest of recent emails from Gmail"
                )
                tools.append(digest_tool)
                
            if GmailSearchTool is not None:
                # Create Gmail search tool
                search_tool = GmailSearchTool(
                    user_id=self.user_id,
                    name="gmail_search", 
                    description="Search Gmail messages using Gmail search syntax"
                )
                tools.append(search_tool)
                
        except Exception as e:
            logger.warning(f"Failed to create Gmail tools: {e}")
            # Continue with empty tools list
            
        return tools
    
    async def get_agent_executor(self) -> CustomizableAgentExecutor:
        """Get or create agent executor using existing framework."""
        if self.executor is None:
            try:
                # Use the existing database-driven agent loading system
                from src.core.agent_loader_db import load_agent_executor_db
                
                self.executor = load_agent_executor_db(
                    agent_name=self.agent_name,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                logger.info(f"Created email digest agent executor for user {self.user_id}")
                
            except Exception as e:
                logger.error(f"Failed to create agent executor via database: {e}")
                # Fallback to direct creation using agent config
                try:
                    self.executor = CustomizableAgentExecutor.from_agent_config(
                        agent_config_dict=self.agent_config,
                        tools=self.tools,
                        user_id=self.user_id,
                        session_id=self.session_id
                    )
                    logger.info(f"Created email digest agent executor via fallback for user {self.user_id}")
                except Exception as fallback_error:
                    logger.error(f"Fallback agent creation also failed: {fallback_error}")
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
            "tools": [tool.name if hasattr(tool, 'name') else str(tool) for tool in self.tools],
            "capabilities": self.agent_config["capabilities"],
            "status": "ready"
        }


async def create_email_digest_agent(user_id: str, session_id: str = None) -> EmailDigestAgent:
    """Factory function to create and initialize an email digest agent.
    
    Args:
        user_id: User ID for context
        session_id: Session ID for memory (optional, will generate if not provided)
        
    Returns:
        Initialized email digest agent
    """
    if not session_id:
        session_id = f"email_digest_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    agent = EmailDigestAgent(user_id, session_id)
    
    # Agent executor will be created on first use
    return agent 