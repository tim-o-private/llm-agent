"""Unit tests for Gmail service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import httpx

from chatServer.services.gmail_service import GmailService
from chatServer.models.external_api import (
    ServiceName, ExternalAPIConnectionResponse, EmailDigestRequest
)


@pytest.fixture
def mock_db_client():
    """Mock Supabase client."""
    mock_client = AsyncMock()
    return mock_client


@pytest.fixture
def gmail_service(mock_db_client):
    """Gmail service instance with mocked dependencies."""
    return GmailService(mock_db_client)


@pytest.fixture
def mock_connection():
    """Mock API connection."""
    return ExternalAPIConnectionResponse(
        id="test-id",
        user_id="test-user",
        service_name=ServiceName.GMAIL,
        token_expires_at=datetime.now() + timedelta(hours=1),
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        service_user_id="test@example.com",
        service_user_email="test@example.com",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_active=True
    )


@pytest.fixture
def mock_gmail_message():
    """Mock Gmail API message response."""
    return {
        "id": "msg123",
        "threadId": "thread123",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"}
            ],
            "mimeType": "text/plain",
            "body": {
                "data": "VGVzdCBtZXNzYWdlIGJvZHk="  # Base64 encoded "Test message body"
            }
        }
    }


class TestGmailService:
    """Test cases for Gmail service."""
    
    @pytest.mark.asyncio
    async def test_get_auth_headers(self, gmail_service, mock_connection):
        """Test authentication header generation."""
        # Mock access token
        mock_connection.access_token = "test-access-token"
        
        headers = await gmail_service._get_auth_headers(mock_connection)
        
        assert headers["Authorization"] == "Bearer test-access-token"
        assert headers["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_get_connection_success(self, gmail_service, mock_db_client):
        """Test successful connection retrieval."""
        # Mock database response
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = AsyncMock(
            data=[{
                "id": "test-id",
                "user_id": "test-user",
                "service_name": "gmail",
                "token_expires_at": "2024-01-01T12:00:00Z",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
                "service_user_id": "test@example.com",
                "service_user_email": "test@example.com",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:00:00Z",
                "is_active": True
            }]
        )
        
        connection = await gmail_service.get_connection("test-user")
        
        assert connection is not None
        assert connection.service_name == ServiceName.GMAIL
        assert connection.user_id == "test-user"
    
    @pytest.mark.asyncio
    async def test_get_connection_not_found(self, gmail_service, mock_db_client):
        """Test connection retrieval when no connection exists."""
        # Mock empty database response
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = AsyncMock(
            data=[]
        )
        
        connection = await gmail_service.get_connection("test-user")
        
        assert connection is None
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, gmail_service):
        """Test successful connection test."""
        with patch.object(gmail_service, 'make_request', return_value={"emailAddress": "test@example.com"}):
            result = await gmail_service.test_connection("test-user")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, gmail_service):
        """Test failed connection test."""
        with patch.object(gmail_service, 'make_request', return_value=None):
            result = await gmail_service.test_connection("test-user")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_messages_success(self, gmail_service):
        """Test successful message retrieval."""
        mock_response = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"}
            ]
        }
        
        with patch.object(gmail_service, 'make_request', return_value=mock_response):
            result = await gmail_service.get_messages("test-user", query="is:unread")
            
            assert result == mock_response
            assert len(result["messages"]) == 2
    
    @pytest.mark.asyncio
    async def test_parse_message_headers(self, gmail_service):
        """Test message header parsing."""
        headers = [
            {"name": "Subject", "value": "Test Subject"},
            {"name": "From", "value": "sender@example.com"},
            {"name": "To", "value": "recipient@example.com"}
        ]
        
        parsed = gmail_service._parse_message_headers(headers)
        
        assert parsed["subject"] == "Test Subject"
        assert parsed["from"] == "sender@example.com"
        assert parsed["to"] == "recipient@example.com"
    
    def test_decode_message_body_plain_text(self, gmail_service):
        """Test message body decoding for plain text."""
        payload = {
            "mimeType": "text/plain",
            "body": {
                "data": "VGVzdCBtZXNzYWdlIGJvZHk="  # Base64 encoded "Test message body"
            }
        }
        
        body = gmail_service._decode_message_body(payload)
        assert body == "Test message body"
    
    def test_decode_message_body_multipart(self, gmail_service):
        """Test message body decoding for multipart messages."""
        payload = {
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": "VGVzdCBtZXNzYWdlIGJvZHk="  # Base64 encoded "Test message body"
                    }
                }
            ]
        }
        
        body = gmail_service._decode_message_body(payload)
        assert body == "Test message body"
    
    def test_parse_email_message(self, gmail_service, mock_gmail_message):
        """Test email message parsing."""
        email_message = gmail_service._parse_email_message(mock_gmail_message)
        
        assert email_message.id == "msg123"
        assert email_message.thread_id == "thread123"
        assert email_message.subject == "Test Subject"
        assert email_message.sender == "sender@example.com"
        assert email_message.recipient == "recipient@example.com"
        assert email_message.body == "Test message body"
        assert email_message.is_read is True  # No UNREAD label
    
    @pytest.mark.asyncio
    async def test_get_recent_emails(self, gmail_service):
        """Test recent email retrieval."""
        request = EmailDigestRequest(hours_back=24, max_threads=10)
        
        # Mock messages response
        mock_messages_response = {
            "messages": [{"id": "msg123", "threadId": "thread123"}]
        }
        
        # Mock message details response
        mock_message_details = {
            "id": "msg123",
            "threadId": "thread123",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"}
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": "VGVzdCBtZXNzYWdlIGJvZHk="
                }
            }
        }
        
        with patch.object(gmail_service, 'get_messages', return_value=mock_messages_response), \
             patch.object(gmail_service, 'get_message_details', return_value=mock_message_details):
            
            emails = await gmail_service.get_recent_emails("test-user", request)
            
            assert len(emails) == 1
            assert emails[0].subject == "Test Subject"
            assert emails[0].sender == "sender@example.com"
    
    @pytest.mark.asyncio
    async def test_get_email_threads(self, gmail_service):
        """Test email thread retrieval and grouping."""
        request = EmailDigestRequest(hours_back=24, max_threads=10)
        
        # Mock recent emails with same thread ID
        mock_emails = [
            MagicMock(
                thread_id="thread123",
                subject="Test Subject",
                sender="sender1@example.com",
                recipient="recipient@example.com",
                date=datetime.now(),
                is_read=False
            ),
            MagicMock(
                thread_id="thread123",
                subject="Re: Test Subject",
                sender="sender2@example.com",
                recipient="recipient@example.com",
                date=datetime.now() + timedelta(minutes=30),
                is_read=True
            )
        ]
        
        with patch.object(gmail_service, 'get_recent_emails', return_value=mock_emails):
            threads = await gmail_service.get_email_threads("test-user", request)
            
            assert len(threads) == 1
            thread = threads[0]
            assert thread.id == "thread123"
            assert thread.message_count == 2
            assert thread.is_unread is True  # Has unread messages
            assert len(thread.participants) == 3  # sender1, sender2, recipient
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, gmail_service):
        """Test rate limiting functionality."""
        user_id = "test-user"
        
        # Test that rate limit allows initial requests
        is_allowed, wait_time = await gmail_service._check_rate_limit(user_id)
        assert is_allowed is True
        assert wait_time is None
        
        # Simulate hitting rate limit
        rate_limit = gmail_service._get_rate_limit_info(user_id)
        rate_limit.current_minute_count = rate_limit.requests_per_minute
        
        is_allowed, wait_time = await gmail_service._check_rate_limit(user_id)
        assert is_allowed is False
        assert wait_time is not None
        assert wait_time > 0
    
    @pytest.mark.asyncio
    async def test_caching(self, gmail_service):
        """Test caching functionality."""
        cache_key = "test:user:endpoint:param=value"
        test_data = {"test": "data"}
        
        # Test cache miss
        cached_data = gmail_service._get_from_cache(cache_key)
        assert cached_data is None
        
        # Test cache set and hit
        gmail_service._set_cache(cache_key, test_data, 300)
        cached_data = gmail_service._get_from_cache(cache_key)
        assert cached_data == test_data
        
        # Test cache expiration
        gmail_service._set_cache(cache_key, test_data, -1)  # Already expired
        cached_data = gmail_service._get_from_cache(cache_key)
        assert cached_data is None 