"""Unit tests for prompt customization service."""

import unittest
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status

from chatServer.models.prompt_customization import PromptCustomizationCreate
from chatServer.services.prompt_customization import PromptCustomizationService, get_prompt_customization_service


@pytest.mark.asyncio
async def test_create_prompt_customization_success():
    """Test successful prompt customization creation."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"
    customization_id = "custom-123"

    customization_data = PromptCustomizationCreate(
        agent_name=agent_name,
        instructions="Always respond in bullet points.",
        is_active=True,
    )

    expected_response = {
        "id": customization_id,
        "user_id": user_id,
        "agent_name": agent_name,
        "instructions": "Always respond in bullet points.",
        "is_active": True,
    }

    mock_response = MagicMock()
    mock_response.data = [expected_response]
    mock_response.error = None

    mock_supabase_client.table.return_value.insert.return_value.execute = AsyncMock(return_value=mock_response)

    result = await service.create_prompt_customization(
        customization_data=customization_data,
        user_id=user_id,
        supabase_client=mock_supabase_client
    )

    assert result == expected_response
    mock_supabase_client.table.assert_called_once_with("user_agent_prompt_customizations")


@pytest.mark.asyncio
async def test_create_prompt_customization_no_data():
    """Test prompt customization creation with no data returned."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"

    customization_data = PromptCustomizationCreate(
        agent_name=agent_name,
        instructions="Test instructions",
        is_active=True,
    )

    mock_response = MagicMock()
    mock_response.data = None
    mock_response.error = MagicMock()
    mock_response.error.message = "Database error"

    mock_supabase_client.table.return_value.insert.return_value.execute = AsyncMock(return_value=mock_response)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_prompt_customization(
            customization_data=customization_data,
            user_id=user_id,
            supabase_client=mock_supabase_client
        )

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to create prompt customization" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_prompt_customization_exception():
    """Test prompt customization creation with exception."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"

    customization_data = PromptCustomizationCreate(
        agent_name=agent_name,
        instructions="Test instructions",
        is_active=True,
    )

    mock_supabase_client.table.return_value.insert.return_value.execute = AsyncMock(
        side_effect=Exception("Database connection failed")
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.create_prompt_customization(
            customization_data=customization_data,
            user_id=user_id,
            supabase_client=mock_supabase_client
        )

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Database connection failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_prompt_customizations_for_agent_success():
    """Test successful retrieval of prompt customizations for agent."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"

    expected_data = [
        {
            "id": "custom-1",
            "user_id": user_id,
            "agent_name": agent_name,
            "instructions": "Always use bullet points.",
            "is_active": True,
        },
    ]

    mock_response = MagicMock()
    mock_response.data = expected_data

    mock_query = mock_supabase_client.table.return_value.select.return_value
    mock_query.eq.return_value.eq.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)

    result = await service.get_prompt_customizations_for_agent(
        agent_name=agent_name,
        user_id=user_id,
        supabase_client=mock_supabase_client
    )

    assert result == expected_data
    mock_supabase_client.table.assert_called_once_with("user_agent_prompt_customizations")


@pytest.mark.asyncio
async def test_get_prompt_customizations_for_agent_empty():
    """Test retrieval of prompt customizations with no data."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"

    mock_response = MagicMock()
    mock_response.data = None

    mock_query = mock_supabase_client.table.return_value.select.return_value
    mock_query.eq.return_value.eq.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)

    result = await service.get_prompt_customizations_for_agent(
        agent_name=agent_name,
        user_id=user_id,
        supabase_client=mock_supabase_client
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_prompt_customizations_for_agent_exception():
    """Test retrieval of prompt customizations with exception."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"

    mock_query = mock_supabase_client.table.return_value.select.return_value
    mock_query.eq.return_value.eq.return_value.eq.return_value.execute = AsyncMock(
        side_effect=Exception("Database query failed")
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_prompt_customizations_for_agent(
            agent_name=agent_name,
            user_id=user_id,
            supabase_client=mock_supabase_client
        )

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Database query failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_user_instructions_success():
    """Test successful retrieval of user instructions."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()

    mock_response = MagicMock()
    mock_response.data = {"instructions": "Always use bullet points."}

    mock_query = mock_supabase_client.table.return_value.select.return_value
    mock_query.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(return_value=mock_response)

    result = await service.get_user_instructions(
        agent_name="assistant",
        user_id="user-123",
        supabase_client=mock_supabase_client
    )

    assert result == "Always use bullet points."


@pytest.mark.asyncio
async def test_get_user_instructions_none():
    """Test retrieval of user instructions when no row exists."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()

    mock_response = MagicMock()
    mock_response.data = None

    mock_query = mock_supabase_client.table.return_value.select.return_value
    mock_query.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(return_value=mock_response)

    result = await service.get_user_instructions(
        agent_name="assistant",
        user_id="user-123",
        supabase_client=mock_supabase_client
    )

    assert result is None


@pytest.mark.asyncio
async def test_update_prompt_customization_success():
    """Test successful prompt customization update."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"
    customization_id = "custom-123"

    customization_data = PromptCustomizationCreate(
        agent_name=agent_name,
        instructions="Updated instructions",
        is_active=True,
    )

    expected_response = {
        "id": customization_id,
        "user_id": user_id,
        "agent_name": agent_name,
        "instructions": "Updated instructions",
        "is_active": True,
    }

    mock_response = MagicMock()
    mock_response.data = [expected_response]
    mock_response.error = None

    mock_query = mock_supabase_client.table.return_value.update.return_value
    mock_query.eq.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)

    result = await service.update_prompt_customization(
        customization_id=customization_id,
        customization_data=customization_data,
        user_id=user_id,
        supabase_client=mock_supabase_client
    )

    assert result == expected_response
    mock_supabase_client.table.assert_called_once_with("user_agent_prompt_customizations")


@pytest.mark.asyncio
async def test_update_prompt_customization_not_found():
    """Test prompt customization update with not found error."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"
    customization_id = "custom-123"

    customization_data = PromptCustomizationCreate(
        agent_name=agent_name,
        instructions="Updated instructions",
        is_active=True,
    )

    mock_response = MagicMock()
    mock_response.data = None
    mock_response.error = MagicMock()
    mock_response.error.code = 'PGRST116'

    mock_query = mock_supabase_client.table.return_value.update.return_value
    mock_query.eq.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_prompt_customization(
            customization_id=customization_id,
            customization_data=customization_data,
            user_id=user_id,
            supabase_client=mock_supabase_client
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found or access denied" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_prompt_customization_no_data():
    """Test prompt customization update with no data returned."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"
    customization_id = "custom-123"

    customization_data = PromptCustomizationCreate(
        agent_name=agent_name,
        instructions="Updated instructions",
        is_active=True,
    )

    mock_response = MagicMock()
    mock_response.data = None
    mock_response.error = None

    mock_query = mock_supabase_client.table.return_value.update.return_value
    mock_query.eq.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_prompt_customization(
            customization_id=customization_id,
            customization_data=customization_data,
            user_id=user_id,
            supabase_client=mock_supabase_client
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found, access denied, or no changes made" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_prompt_customization_exception():
    """Test prompt customization update with exception."""
    service = PromptCustomizationService()
    mock_supabase_client = MagicMock()
    user_id = "test-user-123"
    agent_name = "test-agent"
    customization_id = "custom-123"

    customization_data = PromptCustomizationCreate(
        agent_name=agent_name,
        instructions="Updated instructions",
        is_active=True,
    )

    mock_query = mock_supabase_client.table.return_value.update.return_value
    mock_query.eq.return_value.eq.return_value.execute = AsyncMock(
        side_effect=Exception("Database update failed")
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.update_prompt_customization(
            customization_id=customization_id,
            customization_data=customization_data,
            user_id=user_id,
            supabase_client=mock_supabase_client
        )

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Database update failed" in exc_info.value.detail


class TestPromptCustomizationService(unittest.TestCase):
    """Test cases for PromptCustomizationService class (non-async tests only)."""

    def setUp(self):
        self.service = PromptCustomizationService()

    def test_service_initialization(self):
        self.assertIsInstance(self.service, PromptCustomizationService)


class TestPromptCustomizationServiceGlobal(unittest.TestCase):
    """Test cases for global prompt customization service functions."""

    def setUp(self):
        import chatServer.services.prompt_customization
        chatServer.services.prompt_customization._prompt_customization_service = None

    def test_get_prompt_customization_service_creates_instance(self):
        service = get_prompt_customization_service()
        self.assertIsInstance(service, PromptCustomizationService)

    def test_get_prompt_customization_service_returns_same_instance(self):
        service1 = get_prompt_customization_service()
        service2 = get_prompt_customization_service()
        self.assertIs(service1, service2)


if __name__ == "__main__":
    unittest.main()
