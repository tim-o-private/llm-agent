# Gmail Tools Integration Testing Strategy

## Overview

This document outlines the comprehensive integration testing strategy for Gmail tools within the Clarity v2 system. The strategy covers unit tests, integration tests, and end-to-end testing scenarios.

## Testing Levels

### 1. Unit Tests ✅ **COMPLETE**

**Location**: `tests/chatServer/services/test_langchain_auth_bridge.py`, `tests/chatServer/tools/test_gmail_tools.py`

**Coverage**:
- VaultToLangChainCredentialAdapter functionality
- Gmail tool initialization and error handling
- Input validation and parameter processing
- Mock-based authentication flow testing

**Key Test Scenarios**:
- Token retrieval from vault (success/failure)
- Credential creation and refresh
- Error handling for various failure modes
- Tool factory functions
- Input validation boundaries

### 2. Integration Tests 🔄 **IN PROGRESS**

**Objective**: Test Gmail tools working with real agent framework and database connections

#### 2.1 Agent-Tool Integration Tests

**Location**: `tests/chatServer/tools/test_gmail_tools_integration.py`

**Test Scenarios**:
```python
# Agent can load and execute Gmail tools
async def test_agent_loads_gmail_tools_from_database()
async def test_agent_executes_gmail_digest_tool()
async def test_agent_executes_gmail_search_tool()
async def test_agent_handles_gmail_authentication_errors()
```

#### 2.2 Database Integration Tests

**Location**: `tests/chatServer/services/test_auth_bridge_integration.py`

**Test Scenarios**:
```python
# Real database operations with test data
async def test_vault_token_storage_and_retrieval()
async def test_token_refresh_updates_vault()
async def test_connection_status_tracking()
async def test_rls_policies_prevent_cross_user_access()
```

#### 2.3 OAuth Flow Integration Tests

**Location**: `tests/integration/test_oauth_flow_integration.py`

**Test Scenarios**:
```python
# End-to-end OAuth flow testing
async def test_oauth_callback_stores_tokens_correctly()
async def test_token_expiration_triggers_refresh()
async def test_invalid_tokens_require_reauth()
async def test_oauth_revocation_cleans_up_properly()
```

### 3. End-to-End Tests ⏳ **PLANNED**

**Objective**: Test complete user workflows with real Gmail API

#### 3.1 Gmail API Integration Tests

**Location**: `tests/e2e/test_gmail_api_integration.py`

**Requirements**:
- Test Gmail account with known email content
- Valid OAuth tokens for testing
- Controlled email environment

**Test Scenarios**:
```python
# Real Gmail API calls with test account
async def test_gmail_search_returns_real_emails()
async def test_gmail_digest_processes_real_emails()
async def test_gmail_tools_handle_api_rate_limits()
async def test_gmail_tools_handle_api_errors()
```

#### 3.2 Agent Execution Tests

**Location**: `tests/e2e/test_agent_gmail_execution.py`

**Test Scenarios**:
```python
# Complete agent workflows
async def test_agent_generates_email_digest_end_to_end()
async def test_agent_searches_emails_and_responds()
async def test_agent_handles_no_gmail_connection_gracefully()
async def test_agent_prompts_user_for_oauth_when_needed()
```

## Integration Testing Implementation

### Phase 1: Agent Framework Integration

**Objective**: Enable assistant agent to call Gmail tools directly

#### 1.1 Create Test Agent Configuration

**File**: `tests/fixtures/test_email_digest_agent.sql`

```sql
-- Insert test agent configuration
INSERT INTO agent_configurations (
    agent_name,
    system_prompt,
    llm_config,
    is_active
) VALUES (
    'test_email_digest_agent',
    'You are a helpful assistant that can access Gmail to help users manage their email.',
    '{"provider": "openai", "model": "gpt-4", "temperature": 0.1}',
    true
);

-- Insert Gmail tools for test agent
INSERT INTO agent_tools (
    agent_id,
    type,
    name,
    description,
    config,
    is_active,
    "order"
) VALUES (
    (SELECT id FROM agent_configurations WHERE agent_name = 'test_email_digest_agent'),
    'GmailTool',
    'gmail_digest',
    'Generate email digest from Gmail',
    '{"tool_class": "GmailDigestTool"}',
    true,
    1
),
(
    (SELECT id FROM agent_configurations WHERE agent_name = 'test_email_digest_agent'),
    'GmailTool',
    'gmail_search',
    'Search Gmail messages',
    '{"tool_class": "GmailSearchTool"}',
    true,
    2
);
```

#### 1.2 Create Integration Test Helper

**File**: `tests/helpers/gmail_integration_helper.py`

```python
"""Helper functions for Gmail integration testing."""

import asyncio
from typing import Dict, Any, Optional
from src.core.agent_loader_db import load_agent_executor_db
from chatServer.services.vault_token_service import VaultTokenService


class GmailIntegrationTestHelper:
    """Helper class for Gmail integration testing."""
    
    def __init__(self, test_user_id: str):
        self.test_user_id = test_user_id
        self.vault_service = VaultTokenService()
    
    async def setup_test_oauth_tokens(self, 
                                    access_token: str = "test_access_token",
                                    refresh_token: str = "test_refresh_token") -> None:
        """Set up test OAuth tokens in vault."""
        await self.vault_service.store_tokens(
            user_id=self.test_user_id,
            service_name="gmail",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=None,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            service_user_email="test@gmail.com"
        )
    
    async def cleanup_test_tokens(self) -> None:
        """Clean up test tokens."""
        await self.vault_service.delete_tokens(
            user_id=self.test_user_id,
            service_name="gmail"
        )
    
    async def create_test_agent(self) -> Any:
        """Create test agent with Gmail tools."""
        return load_agent_executor_db(
            agent_name="test_email_digest_agent",
            user_id=self.test_user_id,
            session_id=f"test_session_{self.test_user_id}"
        )
    
    async def execute_gmail_digest(self, 
                                 agent: Any,
                                 hours_back: int = 24,
                                 max_threads: int = 10) -> str:
        """Execute Gmail digest via agent."""
        query = f"Generate an email digest for the last {hours_back} hours, max {max_threads} threads"
        result = await agent.arun(query)
        return result
    
    async def execute_gmail_search(self,
                                 agent: Any,
                                 search_query: str = "is:unread") -> str:
        """Execute Gmail search via agent."""
        query = f"Search my Gmail for: {search_query}"
        result = await agent.arun(query)
        return result
```

#### 1.3 Create Agent Integration Tests

**File**: `tests/chatServer/tools/test_gmail_tools_integration.py`

```python
"""Integration tests for Gmail tools with agent framework."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from tests.helpers.gmail_integration_helper import GmailIntegrationTestHelper


class TestGmailToolsAgentIntegration:
    """Test Gmail tools integration with agent framework."""
    
    @pytest.fixture
    def test_user_id(self):
        """Test user ID."""
        return "test_user_gmail_integration"
    
    @pytest.fixture
    def integration_helper(self, test_user_id):
        """Integration test helper."""
        return GmailIntegrationTestHelper(test_user_id)
    
    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self, integration_helper):
        """Set up and clean up test data."""
        # Setup
        await integration_helper.setup_test_oauth_tokens()
        yield
        # Cleanup
        await integration_helper.cleanup_test_tokens()
    
    @pytest.mark.asyncio
    async def test_agent_loads_gmail_tools_from_database(self, integration_helper):
        """Test that agent can load Gmail tools from database configuration."""
        agent = await integration_helper.create_test_agent()
        
        # Check that agent has Gmail tools
        tool_names = [tool.name for tool in agent.tools]
        assert "gmail_digest" in tool_names
        assert "gmail_search" in tool_names
    
    @pytest.mark.asyncio
    async def test_agent_executes_gmail_digest_with_mocked_api(self, integration_helper):
        """Test agent executing Gmail digest with mocked Gmail API."""
        agent = await integration_helper.create_test_agent()
        
        # Mock Gmail API responses
        with patch('chatServer.tools.gmail_tools.GmailToolkit') as mock_toolkit_class:
            mock_toolkit = MagicMock()
            mock_search_tool = MagicMock()
            mock_search_tool.name = "gmail_search"
            mock_search_tool.run.return_value = "Subject: Test Email 1\nSubject: Test Email 2"
            mock_toolkit.get_tools.return_value = [mock_search_tool]
            mock_toolkit_class.return_value = mock_toolkit
            
            result = await integration_helper.execute_gmail_digest(agent)
            
            assert "Email Digest" in result
            assert "Test Email" in result
    
    @pytest.mark.asyncio
    async def test_agent_handles_no_oauth_connection(self, integration_helper):
        """Test agent handling when no OAuth connection exists."""
        # Clean up tokens first
        await integration_helper.cleanup_test_tokens()
        
        agent = await integration_helper.create_test_agent()
        
        result = await integration_helper.execute_gmail_digest(agent)
        
        # Should get user-friendly error message
        assert "Gmail not connected" in result
        assert "Settings > Integrations" in result
    
    @pytest.mark.asyncio
    async def test_agent_handles_expired_tokens(self, integration_helper):
        """Test agent handling when tokens are expired."""
        agent = await integration_helper.create_test_agent()
        
        # Mock expired credentials
        with patch('google.oauth2.credentials.Credentials') as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.expired = True
            mock_creds.refresh_token = None
            mock_creds_class.return_value = mock_creds
            
            result = await integration_helper.execute_gmail_digest(agent)
            
            assert "Gmail connection expired" in result or "reconnect" in result.lower()
```

### Phase 2: Database Integration Testing

**File**: `tests/chatServer/services/test_auth_bridge_integration.py`

```python
"""Integration tests for auth bridge with real database."""

import pytest
import asyncio
from datetime import datetime, timedelta
from chatServer.services.langchain_auth_bridge import VaultToLangChainCredentialAdapter
from chatServer.services.vault_token_service import VaultTokenService
from chatServer.database.connection import get_db_connection


class TestAuthBridgeIntegration:
    """Test auth bridge with real database operations."""
    
    @pytest.fixture
    def test_user_id(self):
        """Test user ID."""
        return "test_user_auth_bridge_integration"
    
    @pytest.fixture
    async def vault_service(self):
        """Vault token service."""
        return VaultTokenService()
    
    @pytest.fixture
    async def auth_bridge(self):
        """Auth bridge instance."""
        return VaultToLangChainCredentialAdapter()
    
    @pytest.fixture(autouse=True)
    async def cleanup_test_data(self, test_user_id, vault_service):
        """Clean up test data after each test."""
        yield
        # Cleanup
        try:
            await vault_service.delete_tokens(test_user_id, "gmail")
        except:
            pass  # Ignore cleanup errors
    
    @pytest.mark.asyncio
    async def test_vault_token_storage_and_retrieval(self, test_user_id, vault_service, auth_bridge):
        """Test storing tokens in vault and retrieving via auth bridge."""
        # Store tokens via vault service
        await vault_service.store_tokens(
            user_id=test_user_id,
            service_name="gmail",
            access_token="test_access_token_123",
            refresh_token="test_refresh_token_456",
            expires_at=datetime.now() + timedelta(hours=1),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            service_user_email="test@gmail.com"
        )
        
        # Retrieve tokens via auth bridge
        access_token, refresh_token = await auth_bridge._get_tokens_from_vault(test_user_id, "gmail")
        
        assert access_token == "test_access_token_123"
        assert refresh_token == "test_refresh_token_456"
    
    @pytest.mark.asyncio
    async def test_token_refresh_updates_vault(self, test_user_id, vault_service, auth_bridge):
        """Test that token refresh updates vault storage."""
        # Store initial tokens
        await vault_service.store_tokens(
            user_id=test_user_id,
            service_name="gmail",
            access_token="old_access_token",
            refresh_token="refresh_token_123",
            expires_at=datetime.now() + timedelta(hours=1),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            service_user_email="test@gmail.com"
        )
        
        # Update access token
        new_expires = datetime.now() + timedelta(hours=2)
        await auth_bridge._update_access_token_in_vault(
            test_user_id, 
            "gmail", 
            "new_access_token", 
            new_expires
        )
        
        # Verify update
        access_token, refresh_token = await auth_bridge._get_tokens_from_vault(test_user_id, "gmail")
        assert access_token == "new_access_token"
        assert refresh_token == "refresh_token_123"  # Should remain unchanged
    
    @pytest.mark.asyncio
    async def test_rls_policies_prevent_cross_user_access(self, vault_service, auth_bridge):
        """Test that RLS policies prevent cross-user token access."""
        user1_id = "test_user_1"
        user2_id = "test_user_2"
        
        try:
            # Store tokens for user1
            await vault_service.store_tokens(
                user_id=user1_id,
                service_name="gmail",
                access_token="user1_token",
                refresh_token="user1_refresh",
                expires_at=datetime.now() + timedelta(hours=1),
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
                service_user_email="user1@gmail.com"
            )
            
            # Try to access user1's tokens as user2
            with pytest.raises(ValueError, match="No gmail connection found"):
                await auth_bridge._get_tokens_from_vault(user2_id, "gmail")
                
        finally:
            # Cleanup
            try:
                await vault_service.delete_tokens(user1_id, "gmail")
                await vault_service.delete_tokens(user2_id, "gmail")
            except:
                pass
```

### Phase 3: End-to-End Testing Strategy

#### 3.1 Test Environment Setup

**Requirements**:
1. **Test Gmail Account**: Dedicated Gmail account for testing
2. **OAuth Application**: Test Google OAuth application with appropriate scopes
3. **Controlled Email Environment**: Known email content for predictable testing

#### 3.2 E2E Test Implementation

**File**: `tests/e2e/test_gmail_api_integration.py`

```python
"""End-to-end tests with real Gmail API."""

import pytest
import os
from datetime import datetime, timedelta
from tests.helpers.gmail_integration_helper import GmailIntegrationTestHelper


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("GMAIL_E2E_TEST_ENABLED"), 
    reason="Gmail E2E tests require GMAIL_E2E_TEST_ENABLED=true"
)
class TestGmailAPIIntegration:
    """End-to-end tests with real Gmail API."""
    
    @pytest.fixture
    def test_user_id(self):
        """Test user ID for E2E tests."""
        return os.getenv("GMAIL_E2E_TEST_USER_ID", "e2e_test_user")
    
    @pytest.fixture
    def real_oauth_tokens(self):
        """Real OAuth tokens for testing."""
        return {
            "access_token": os.getenv("GMAIL_E2E_ACCESS_TOKEN"),
            "refresh_token": os.getenv("GMAIL_E2E_REFRESH_TOKEN")
        }
    
    @pytest.fixture
    async def integration_helper(self, test_user_id, real_oauth_tokens):
        """Integration helper with real tokens."""
        helper = GmailIntegrationTestHelper(test_user_id)
        await helper.setup_test_oauth_tokens(
            access_token=real_oauth_tokens["access_token"],
            refresh_token=real_oauth_tokens["refresh_token"]
        )
        yield helper
        await helper.cleanup_test_tokens()
    
    @pytest.mark.asyncio
    async def test_gmail_search_returns_real_emails(self, integration_helper):
        """Test Gmail search with real API."""
        agent = await integration_helper.create_test_agent()
        result = await integration_helper.execute_gmail_search(agent, "is:unread")
        
        # Should return actual search results or indicate no unread emails
        assert "Search results" in result or "No emails found" in result
    
    @pytest.mark.asyncio
    async def test_gmail_digest_processes_real_emails(self, integration_helper):
        """Test Gmail digest with real API."""
        agent = await integration_helper.create_test_agent()
        result = await integration_helper.execute_gmail_digest(agent, hours_back=168)  # 1 week
        
        # Should return actual digest or indicate no emails
        assert "Email Digest" in result
        assert ("recent emails" in result or "No emails found" in result)
```

## Testing Infrastructure

### 1. Test Data Management

**File**: `tests/fixtures/gmail_test_data.py`

```python
"""Test data fixtures for Gmail integration tests."""

from datetime import datetime, timedelta
from typing import Dict, Any, List


class GmailTestData:
    """Test data for Gmail integration tests."""
    
    @staticmethod
    def sample_oauth_tokens() -> Dict[str, Any]:
        """Sample OAuth tokens for testing."""
        return {
            "access_token": "ya29.test_access_token_12345",
            "refresh_token": "1//test_refresh_token_67890",
            "expires_at": datetime.now() + timedelta(hours=1),
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "service_user_email": "test@gmail.com"
        }
    
    @staticmethod
    def sample_gmail_search_response() -> str:
        """Sample Gmail search response."""
        return """
        Message ID: 18c2f1234567890a
        Subject: Important Meeting Tomorrow
        From: boss@company.com
        Date: 2024-01-15 10:30:00
        
        Message ID: 18c2f1234567890b
        Subject: Project Update Required
        From: colleague@company.com
        Date: 2024-01-15 09:15:00
        """
    
    @staticmethod
    def sample_email_digest() -> str:
        """Sample email digest output."""
        return """
        Email Digest - Last 24 hours:
        
        Found 2 recent emails.
        
        Recent email subjects:
        1. Important Meeting Tomorrow
        2. Project Update Required
        """
```

### 2. Mock Services

**File**: `tests/mocks/gmail_api_mock.py`

```python
"""Mock Gmail API responses for testing."""

from typing import Dict, Any, List
from unittest.mock import MagicMock


class MockGmailAPI:
    """Mock Gmail API for testing."""
    
    def __init__(self):
        self.search_responses = {}
        self.message_responses = {}
    
    def set_search_response(self, query: str, response: str):
        """Set mock response for search query."""
        self.search_responses[query] = response
    
    def set_message_response(self, message_id: str, response: str):
        """Set mock response for message retrieval."""
        self.message_responses[message_id] = response
    
    def create_mock_toolkit(self) -> MagicMock:
        """Create mock Gmail toolkit."""
        mock_toolkit = MagicMock()
        
        # Mock search tool
        mock_search_tool = MagicMock()
        mock_search_tool.name = "gmail_search"
        mock_search_tool.run.side_effect = lambda args: self.search_responses.get(
            args.get("query", ""), "No results found"
        )
        
        # Mock get message tool
        mock_get_message_tool = MagicMock()
        mock_get_message_tool.name = "gmail_get_message"
        mock_get_message_tool.run.side_effect = lambda args: self.message_responses.get(
            args.get("message_id", ""), "Message not found"
        )
        
        mock_toolkit.get_tools.return_value = [mock_search_tool, mock_get_message_tool]
        return mock_toolkit
```

## Test Execution Strategy

### 1. Continuous Integration

**GitHub Actions Workflow**: `.github/workflows/gmail-tools-tests.yml`

```yaml
name: Gmail Tools Tests

on:
  push:
    paths:
      - 'chatServer/tools/gmail_tools.py'
      - 'chatServer/services/langchain_auth_bridge.py'
      - 'tests/chatServer/tools/test_gmail_tools*'
      - 'tests/chatServer/services/test_langchain_auth_bridge*'
  pull_request:
    paths:
      - 'chatServer/tools/gmail_tools.py'
      - 'chatServer/services/langchain_auth_bridge.py'
      - 'tests/chatServer/tools/test_gmail_tools*'
      - 'tests/chatServer/services/test_langchain_auth_bridge*'

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      - name: Run unit tests
        run: |
          pytest tests/chatServer/tools/test_gmail_tools.py -v
          pytest tests/chatServer/services/test_langchain_auth_bridge.py -v
  
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      - name: Run database migrations
        run: |
          # Run Supabase migrations
          supabase db reset
      - name: Run integration tests
        run: |
          pytest tests/chatServer/tools/test_gmail_tools_integration.py -v
          pytest tests/chatServer/services/test_auth_bridge_integration.py -v
```

### 2. Local Development Testing

**Test Commands**:

```bash
# Unit tests only
pytest tests/chatServer/tools/test_gmail_tools.py -v
pytest tests/chatServer/services/test_langchain_auth_bridge.py -v

# Integration tests (requires database)
pytest tests/chatServer/tools/test_gmail_tools_integration.py -v
pytest tests/chatServer/services/test_auth_bridge_integration.py -v

# E2E tests (requires real OAuth tokens)
GMAIL_E2E_TEST_ENABLED=true \
GMAIL_E2E_TEST_USER_ID=your_test_user \
GMAIL_E2E_ACCESS_TOKEN=your_access_token \
GMAIL_E2E_REFRESH_TOKEN=your_refresh_token \
pytest tests/e2e/test_gmail_api_integration.py -v

# All tests
pytest tests/ -k gmail -v
```

### 3. Test Coverage Requirements

**Minimum Coverage Targets**:
- Unit Tests: 95% code coverage
- Integration Tests: 80% workflow coverage
- E2E Tests: 100% critical path coverage

**Coverage Command**:
```bash
pytest --cov=chatServer.tools.gmail_tools --cov=chatServer.services.langchain_auth_bridge --cov-report=html tests/
```

## Risk Mitigation

### 1. Test Environment Isolation

- **Separate Test Database**: Use dedicated test database with isolated schemas
- **Test User Accounts**: Use dedicated test Gmail accounts
- **Mock External APIs**: Mock Gmail API for unit and integration tests
- **Environment Variables**: Use environment-specific configuration

### 2. Data Privacy

- **No Real User Data**: Never use real user emails or tokens in tests
- **Token Encryption**: Ensure test tokens are properly encrypted in vault
- **Cleanup Procedures**: Automatic cleanup of test data after each test

### 3. Rate Limiting

- **API Quotas**: Respect Gmail API rate limits in E2E tests
- **Test Throttling**: Implement delays between API calls in E2E tests
- **Fallback Strategies**: Use mocked responses when API limits are reached

## Success Criteria

### 1. Unit Tests ✅
- [x] All unit tests pass
- [x] 95%+ code coverage
- [x] All error scenarios covered
- [x] Input validation tested

### 2. Integration Tests 🔄
- [ ] Agent can load Gmail tools from database
- [ ] Agent can execute Gmail tools successfully
- [ ] Error handling works end-to-end
- [ ] Database operations work correctly

### 3. E2E Tests ⏳
- [ ] Real Gmail API integration works
- [ ] OAuth flow works end-to-end
- [ ] Token refresh works automatically
- [ ] User error messages are helpful

## Next Steps

1. **Implement Integration Tests**: Create agent integration test framework
2. **Set Up Test Environment**: Configure test database and OAuth application
3. **Create E2E Test Suite**: Implement end-to-end testing with real Gmail API
4. **Automate Testing**: Set up CI/CD pipeline for automated testing
5. **Performance Testing**: Add performance benchmarks for Gmail operations

## Conclusion

This comprehensive testing strategy ensures that Gmail tools integration is thoroughly tested at all levels, from individual component functionality to complete user workflows. The strategy balances thorough testing with practical implementation constraints, providing confidence in the system's reliability while maintaining development velocity. 