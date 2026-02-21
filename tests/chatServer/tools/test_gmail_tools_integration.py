"""Integration tests for Gmail tools with agent framework."""


import pytest

from tests.helpers.gmail_integration_helper import GmailIntegrationTestHelper


@pytest.mark.integration
class TestGmailToolsAgentIntegration:
    """Test Gmail tools integration with agent framework."""

    @pytest.fixture
    def integration_helper(self):
        """Integration test helper with auto-generated UUID."""
        # Let the helper generate a proper UUID instead of passing a string
        return GmailIntegrationTestHelper()

    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self, integration_helper):
        """Set up and clean up test data."""
        # Setup
        await integration_helper.setup_test_oauth_tokens()
        yield
        # Cleanup
        await integration_helper.cleanup_test_tokens()
        await integration_helper.close()

    @pytest.mark.asyncio
    async def test_agent_loads_gmail_tools_from_database(self, integration_helper):
        """Test that agent can load Gmail tools from database configuration."""
        agent = await integration_helper.create_test_agent()

        # Check that agent has Gmail tools
        tool_names = [tool.name for tool in agent.tools]
        assert "gmail_digest" in tool_names
        assert "gmail_search" in tool_names

        # Verify tools are properly configured
        gmail_digest_tool = next((tool for tool in agent.tools if tool.name == "gmail_digest"), None)
        gmail_search_tool = next((tool for tool in agent.tools if tool.name == "gmail_search"), None)

        assert gmail_digest_tool is not None
        assert gmail_search_tool is not None

        # Check that tools have the expected attributes
        assert hasattr(gmail_digest_tool, 'user_id')
        assert hasattr(gmail_search_tool, 'user_id')
        assert gmail_digest_tool.user_id == integration_helper.test_user_id
        assert gmail_search_tool.user_id == integration_helper.test_user_id

    @pytest.mark.asyncio
    async def test_oauth_tokens_accessible_to_tools(self, integration_helper):
        """Test that OAuth tokens stored in database are accessible to Gmail tools."""
        agent = await integration_helper.create_test_agent()

        # Get the Gmail tools
        gmail_digest_tool = next((tool for tool in agent.tools if tool.name == "gmail_digest"), None)
        assert gmail_digest_tool is not None

        # Test that the tool can access the credential adapter
        # This tests the integration between VaultTokenService and LangChain auth bridge
        from chatServer.services.langchain_auth_bridge import VaultToLangChainCredentialAdapter

        # Get database connection for the adapter
        db_conn = await integration_helper._get_db_connection()

        # Create the adapter that the tool would use
        adapter = VaultToLangChainCredentialAdapter(db_connection=db_conn)

        # Test that credentials can be retrieved (this tests the database integration)
        credentials = await adapter.create_google_credentials(
            user_id=integration_helper.test_user_id,
            service_name="gmail"
        )
        assert credentials is not None
        assert hasattr(credentials, 'token')
        assert credentials.token == "test_access_token"

    @pytest.mark.asyncio
    async def test_agent_handles_missing_oauth_tokens(self, integration_helper):
        """Test agent behavior when OAuth tokens are missing from database."""
        # Clean up tokens first to simulate missing OAuth
        await integration_helper.cleanup_test_tokens()

        agent = await integration_helper.create_test_agent()

        # Verify tools are still loaded (they should be, just won't work without OAuth)
        tool_names = [tool.name for tool in agent.tools]
        assert "gmail_digest" in tool_names
        assert "gmail_search" in tool_names

        # Test that credential adapter handles missing tokens gracefully
        from chatServer.services.langchain_auth_bridge import VaultToLangChainCredentialAdapter

        # Get database connection for the adapter
        db_conn = await integration_helper._get_db_connection()
        adapter = VaultToLangChainCredentialAdapter(db_connection=db_conn)

        # Should raise appropriate exception for missing credentials
        try:
            credentials = await adapter.create_google_credentials(
                user_id=integration_helper.test_user_id,
                service_name="gmail"
            )
            # If it returns something, it should be None or empty
            assert credentials is None or not hasattr(credentials, 'token') or not credentials.token
        except Exception as e:
            # Should be a meaningful error about missing credentials
            assert "not found" in str(e).lower() or "missing" in str(e).lower() or "no connection" in str(e).lower() or "no oauth" in str(e).lower()  # noqa: E501

    @pytest.mark.asyncio
    async def test_database_integration_consistency(self, integration_helper):
        """Test that database integration is consistent across multiple agent instances."""
        # Create first agent
        agent1 = await integration_helper.create_test_agent()

        # Create second agent with same user_id
        agent2 = await integration_helper.create_test_agent()

        # Both should have the same tools
        agent1_tools = [tool.name for tool in agent1.tools]
        agent2_tools = [tool.name for tool in agent2.tools]

        assert agent1_tools == agent2_tools
        assert "gmail_digest" in agent1_tools
        assert "gmail_search" in agent1_tools

        # Both should have access to the same OAuth tokens
        from chatServer.services.langchain_auth_bridge import VaultToLangChainCredentialAdapter

        # Get database connection for the adapters
        db_conn = await integration_helper._get_db_connection()
        adapter1 = VaultToLangChainCredentialAdapter(db_connection=db_conn)
        adapter2 = VaultToLangChainCredentialAdapter(db_connection=db_conn)

        credentials1 = await adapter1.create_google_credentials(
            user_id=integration_helper.test_user_id,
            service_name="gmail"
        )
        credentials2 = await adapter2.create_google_credentials(
            user_id=integration_helper.test_user_id,
            service_name="gmail"
        )

        assert credentials1 is not None
        assert credentials2 is not None
        assert credentials1.token == credentials2.token

    @pytest.mark.asyncio
    async def test_user_isolation_in_database(self, integration_helper):
        """Test that different users have isolated access to their OAuth tokens."""
        # Create a second test user
        second_helper = GmailIntegrationTestHelper()
        await second_helper.setup_test_oauth_tokens(
            access_token="second_user_token",
            refresh_token="second_user_refresh"
        )

        try:
            # Test that first user can't access second user's tokens
            from chatServer.services.langchain_auth_bridge import VaultToLangChainCredentialAdapter

            # Get database connections for the adapters
            db_conn1 = await integration_helper._get_db_connection()
            db_conn2 = await second_helper._get_db_connection()

            # First user's adapter
            adapter1 = VaultToLangChainCredentialAdapter(db_connection=db_conn1)

            # Second user's adapter
            adapter2 = VaultToLangChainCredentialAdapter(db_connection=db_conn2)

            credentials1 = await adapter1.create_google_credentials(
                user_id=integration_helper.test_user_id,
                service_name="gmail"
            )
            credentials2 = await adapter2.create_google_credentials(
                user_id=second_helper.test_user_id,
                service_name="gmail"
            )

            # Each user should get their own tokens
            assert credentials1.token == "test_access_token"  # First user's token
            assert credentials2.token == "second_user_token"  # Second user's token
            assert credentials1.token != credentials2.token

        finally:
            # Clean up second user
            await second_helper.cleanup_test_tokens()
            await second_helper.close()
