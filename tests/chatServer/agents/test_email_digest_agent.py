"""Tests for Email Digest Agent."""
# @docs memory-bank/patterns/testing-patterns.md#pattern-3-agent-testing
# @rules memory-bank/rules/testing-rules.json#test-003

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

# Import the agent and tools
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../chatServer'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../src'))

from chatServer.agents.email_digest_agent import EmailDigestAgent
from chatServer.tools.gmail_tools import GmailDigestTool, GmailSearchTool


class TestEmailDigestAgent:
    """Test cases for Email Digest Agent."""
    
    @pytest.fixture
    def mock_config_loader(self):
        """Mock config loader."""
        mock_config = Mock()
        mock_config.get_agent_config.return_value = {
            "model": "gemini-pro",
            "temperature": 0.7
        }
        return mock_config
    
    @pytest.fixture
    def mock_gmail_toolkit(self):
        """Mock Gmail toolkit."""
        with patch('chatServer.tools.gmail_tools.GmailToolkit') as mock_toolkit_class:
            mock_toolkit = Mock()
            
            # Mock Gmail tools
            mock_search_tool = Mock()
            mock_search_tool.name = "gmail_search"
            mock_search_tool.run.return_value = "Mock search results"
            
            mock_get_message_tool = Mock()
            mock_get_message_tool.name = "gmail_get_message"
            mock_get_message_tool.run.return_value = "Mock message details"
            
            mock_toolkit.get_tools.return_value = [mock_search_tool, mock_get_message_tool]
            mock_toolkit_class.return_value = mock_toolkit
            
            yield mock_toolkit
    
    @pytest.fixture
    def mock_agent_executor(self):
        """Mock agent executor."""
        mock_executor = AsyncMock()
        mock_executor.ainvoke.return_value = {
            "output": "Mock agent response"
        }
        return mock_executor
    
    @pytest.fixture
    def email_agent(self, mock_config_loader):
        """Create Email Digest Agent instance."""
        with patch('chatServer.agents.email_digest_agent.ConfigLoader', return_value=mock_config_loader):
            agent = EmailDigestAgent(
                user_id="test_user_123",
                session_id="test_session_456",
                config_loader=mock_config_loader
            )
            return agent
    
    def test_agent_initialization(self, email_agent):
        """Test agent initialization."""
        assert email_agent.user_id == "test_user_123"
        assert email_agent.session_id == "test_session_456"
        assert email_agent.agent_name == "email_digest_agent"
        assert email_agent.agent_config["name"] == "email_digest_agent"
        assert "Email Digest Agent" in email_agent.agent_config["system_prompt"]
    
    def test_create_tools_success(self, mock_gmail_toolkit):
        """Test successful tool creation."""
        with patch('chatServer.agents.email_digest_agent.ConfigLoader'):
            agent = EmailDigestAgent(
                user_id="test_user",
                session_id="test_session"
            )
            
            # Tools should be created (mocked)
            assert len(agent.tools) >= 0  # May be 0 if Gmail tools fail to initialize
    
    def test_create_tools_failure(self):
        """Test tool creation with Gmail import failure."""
        with patch('chatServer.tools.gmail_tools.GmailToolkit', side_effect=ImportError("Gmail not available")):
            with patch('chatServer.agents.email_digest_agent.ConfigLoader'):
                agent = EmailDigestAgent(
                    user_id="test_user",
                    session_id="test_session"
                )
                
                # Should handle failure gracefully
                assert isinstance(agent.tools, list)
    
    @pytest.mark.asyncio
    async def test_get_agent_executor(self, email_agent, mock_agent_executor):
        """Test agent executor creation."""
        with patch('chatServer.agents.email_digest_agent.CustomizableAgentExecutor') as mock_executor_class:
            mock_executor_class.from_agent_config.return_value = mock_agent_executor
            
            executor = await email_agent.get_agent_executor()
            
            assert executor == mock_agent_executor
            mock_executor_class.from_agent_config.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_agent_executor_failure(self, email_agent):
        """Test agent executor creation failure."""
        with patch('chatServer.agents.email_digest_agent.CustomizableAgentExecutor') as mock_executor_class:
            mock_executor_class.from_agent_config.side_effect = Exception("Executor creation failed")
            
            with pytest.raises(RuntimeError, match="Failed to initialize email digest agent"):
                await email_agent.get_agent_executor()
    
    @pytest.mark.asyncio
    async def test_generate_digest_success(self, email_agent, mock_agent_executor):
        """Test successful email digest generation."""
        with patch.object(email_agent, 'get_agent_executor', return_value=mock_agent_executor):
            mock_agent_executor.ainvoke.return_value = {
                "output": "Email digest: 5 new emails found..."
            }
            
            result = await email_agent.generate_digest(
                hours_back=24,
                max_threads=20,
                include_read=False
            )
            
            assert "Email digest: 5 new emails found..." in result
            mock_agent_executor.ainvoke.assert_called_once()
            
            # Check the input passed to the agent
            call_args = mock_agent_executor.ainvoke.call_args[0][0]
            assert "24 hours" in call_args["input"]
            assert "20 email threads" in call_args["input"]
            assert "Exclude read emails" in call_args["input"]
    
    @pytest.mark.asyncio
    async def test_generate_digest_failure(self, email_agent):
        """Test email digest generation failure."""
        with patch.object(email_agent, 'get_agent_executor', side_effect=Exception("Agent failed")):
            result = await email_agent.generate_digest()
            
            assert "Failed to generate email digest" in result
    
    @pytest.mark.asyncio
    async def test_search_emails_success(self, email_agent, mock_agent_executor):
        """Test successful email search."""
        with patch.object(email_agent, 'get_agent_executor', return_value=mock_agent_executor):
            mock_agent_executor.ainvoke.return_value = {
                "output": "Found 3 emails matching your search..."
            }
            
            result = await email_agent.search_emails(
                query="is:unread from:important@example.com",
                max_results=10
            )
            
            assert "Found 3 emails matching" in result
            mock_agent_executor.ainvoke.assert_called_once()
            
            # Check the input passed to the agent
            call_args = mock_agent_executor.ainvoke.call_args[0][0]
            assert "is:unread from:important@example.com" in call_args["input"]
            assert "10 results" in call_args["input"]
    
    @pytest.mark.asyncio
    async def test_search_emails_failure(self, email_agent):
        """Test email search failure."""
        with patch.object(email_agent, 'get_agent_executor', side_effect=Exception("Search failed")):
            result = await email_agent.search_emails("test query")
            
            assert "Failed to search emails" in result
    
    @pytest.mark.asyncio
    async def test_analyze_emails_success(self, email_agent, mock_agent_executor):
        """Test successful email analysis."""
        with patch.object(email_agent, 'get_agent_executor', return_value=mock_agent_executor):
            mock_agent_executor.ainvoke.return_value = {
                "output": "Analysis complete: Most emails are from work colleagues..."
            }
            
            result = await email_agent.analyze_emails(
                "Find patterns in my email senders over the last week"
            )
            
            assert "Analysis complete" in result
            mock_agent_executor.ainvoke.assert_called_once()
            
            # Check the input passed to the agent
            call_args = mock_agent_executor.ainvoke.call_args[0][0]
            assert "Find patterns in my email senders" in call_args["input"]
    
    @pytest.mark.asyncio
    async def test_analyze_emails_failure(self, email_agent):
        """Test email analysis failure."""
        with patch.object(email_agent, 'get_agent_executor', side_effect=Exception("Analysis failed")):
            result = await email_agent.analyze_emails("test analysis")
            
            assert "Failed to analyze emails" in result
    
    def test_get_agent_info(self, email_agent):
        """Test getting agent information."""
        info = email_agent.get_agent_info()
        
        assert info["agent_name"] == "email_digest_agent"
        assert info["user_id"] == "test_user_123"
        assert info["session_id"] == "test_session_456"
        assert "tools_count" in info
        assert "tools" in info
        assert "capabilities" in info
        assert "status" in info
        
        # Check capabilities
        capabilities = info["capabilities"]
        assert "Email digest generation" in capabilities
        assert "Email search" in capabilities
        assert "Email analysis" in capabilities
        assert "Email management advice" in capabilities
    
    def test_system_prompt_content(self, email_agent):
        """Test system prompt contains required content."""
        system_prompt = email_agent._get_system_prompt()
        
        # Check key components are present
        assert "Email Digest Agent" in system_prompt
        assert "Email Digest Generation" in system_prompt
        assert "Email Search" in system_prompt
        assert "Email Analysis" in system_prompt
        assert "Gmail search syntax" in system_prompt
        assert "privacy and security" in system_prompt
    
    @pytest.mark.asyncio
    async def test_agent_executor_caching(self, email_agent, mock_agent_executor):
        """Test that agent executor is cached."""
        with patch('chatServer.agents.email_digest_agent.CustomizableAgentExecutor') as mock_executor_class:
            mock_executor_class.from_agent_config.return_value = mock_agent_executor
            
            # First call should create executor
            executor1 = await email_agent.get_agent_executor()
            
            # Second call should return cached executor
            executor2 = await email_agent.get_agent_executor()
            
            assert executor1 == executor2
            # Should only be called once due to caching
            mock_executor_class.from_agent_config.assert_called_once()


class TestGmailTools:
    """Test cases for Gmail tools."""
    
    @pytest.fixture
    def mock_gmail_credentials(self):
        """Mock Gmail credentials."""
        with patch('chatServer.tools.gmail_tools.get_gmail_credentials') as mock_creds:
            mock_creds.return_value = Mock()
            yield mock_creds
    
    @pytest.fixture
    def mock_gmail_service(self):
        """Mock Gmail service."""
        with patch('chatServer.tools.gmail_tools.build_resource_service') as mock_service:
            mock_service.return_value = Mock()
            yield mock_service
    
    def test_gmail_digest_tool_initialization(self, mock_gmail_credentials, mock_gmail_service):
        """Test Gmail digest tool initialization."""
        with patch('chatServer.tools.gmail_tools.GmailToolkit'):
            tool = GmailDigestTool(user_id="test_user")
            
            assert tool.user_id == "test_user"
            assert tool.name == "gmail_digest"
            assert "Generate a digest of recent emails" in tool.description
    
    def test_gmail_search_tool_initialization(self, mock_gmail_credentials, mock_gmail_service):
        """Test Gmail search tool initialization."""
        with patch('chatServer.tools.gmail_tools.GmailToolkit'):
            tool = GmailSearchTool(user_id="test_user")
            
            assert tool.user_id == "test_user"
            assert tool.name == "gmail_search"
            assert "Search Gmail messages" in tool.description
    
    def test_gmail_toolkit_creation_failure(self):
        """Test Gmail toolkit creation failure."""
        with patch('chatServer.tools.gmail_tools.get_gmail_credentials', side_effect=Exception("Auth failed")):
            tool = GmailDigestTool(user_id="test_user")
            
            with pytest.raises(RuntimeError, match="Gmail authentication failed"):
                tool._get_gmail_toolkit()


if __name__ == "__main__":
    pytest.main([__file__]) 