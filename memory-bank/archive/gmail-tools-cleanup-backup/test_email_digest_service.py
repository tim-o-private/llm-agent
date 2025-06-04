"""Unit tests for Email Digest service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from chatServer.services.email_digest_service import EmailDigestService
from chatServer.models.external_api import (
    EmailDigestRequest, EmailDigestResponse, EmailThread, EmailMessage
)


@pytest.fixture
def mock_db_client():
    """Mock Supabase client."""
    mock_client = AsyncMock()
    return mock_client


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service."""
    mock_service = AsyncMock()
    return mock_service


@pytest.fixture
def mock_llm_interface():
    """Mock LLM interface."""
    mock_llm = AsyncMock()
    mock_llm.llm.ainvoke.return_value = MagicMock(content="Test AI summary")
    return mock_llm


@pytest.fixture
def email_digest_service(mock_db_client):
    """Email digest service instance with mocked dependencies."""
    with patch('chatServer.services.email_digest_service.GmailService') as mock_gmail_class, \
         patch('chatServer.services.email_digest_service.LLMInterface') as mock_llm_class:
        
        service = EmailDigestService(mock_db_client)
        service.gmail_service = AsyncMock()
        service.llm_interface = AsyncMock()
        service.llm_interface.llm.ainvoke.return_value = MagicMock(content="Test AI summary")
        return service


@pytest.fixture
def sample_email_message():
    """Sample email message for testing."""
    return EmailMessage(
        id="msg123",
        thread_id="thread123",
        subject="Test Subject",
        sender="sender@example.com",
        recipient="recipient@example.com",
        body="Test message body",
        date=datetime.now(),
        is_read=False,
        labels=["INBOX", "UNREAD"]
    )


@pytest.fixture
def sample_email_thread(sample_email_message):
    """Sample email thread for testing."""
    return EmailThread(
        id="thread123",
        subject="Test Subject",
        messages=[sample_email_message],
        participants=["sender@example.com", "recipient@example.com"],
        last_message_date=datetime.now(),
        message_count=1,
        is_unread=True
    )


class TestEmailDigestService:
    """Test cases for Email Digest service."""
    
    def test_format_thread_for_summary(self, email_digest_service, sample_email_thread):
        """Test thread formatting for LLM summarization."""
        formatted = email_digest_service._format_thread_for_summary(sample_email_thread)
        
        assert "Thread: Test Subject" in formatted
        assert "Participants: sender@example.com, recipient@example.com" in formatted
        assert "Messages: 1" in formatted
        assert "Unread: Yes" in formatted
        assert "From: sender@example.com" in formatted
        assert "Test message body" in formatted
    
    def test_create_digest_prompt(self, email_digest_service, sample_email_thread):
        """Test digest prompt creation."""
        threads = [sample_email_thread]
        time_period_hours = 24
        
        prompt = email_digest_service._create_digest_prompt(threads, time_period_hours)
        
        assert "last 24 hours" in prompt
        assert "Test Subject" in prompt
        assert "sender@example.com" in prompt
        assert "Important emails that require action" in prompt
        assert "Keep the summary concise" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_summary_with_llm_success(self, email_digest_service, sample_email_thread):
        """Test successful LLM summary generation."""
        threads = [sample_email_thread]
        time_period_hours = 24
        
        summary = await email_digest_service._generate_summary_with_llm(threads, time_period_hours)
        
        assert summary == "Test AI summary"
        email_digest_service.llm_interface.llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_summary_with_llm_failure(self, email_digest_service, sample_email_thread):
        """Test LLM summary generation failure fallback."""
        threads = [sample_email_thread]
        time_period_hours = 24
        
        # Mock LLM failure
        email_digest_service.llm_interface.llm.ainvoke.side_effect = Exception("LLM error")
        
        summary = await email_digest_service._generate_summary_with_llm(threads, time_period_hours)
        
        # Should fall back to basic summary
        assert "Email Digest - Last 24 hours" in summary
        assert "Total threads: 1" in summary
        assert "Unread threads: 1" in summary
    
    def test_generate_fallback_summary_with_threads(self, email_digest_service, sample_email_thread):
        """Test fallback summary generation with threads."""
        threads = [sample_email_thread]
        time_period_hours = 24
        
        summary = email_digest_service._generate_fallback_summary(threads, time_period_hours)
        
        assert "Email Digest - Last 24 hours" in summary
        assert "Total threads: 1" in summary
        assert "Unread threads: 1" in summary
        assert "Test Subject" in summary
        assert "sender@example.com" in summary
    
    def test_generate_fallback_summary_empty(self, email_digest_service):
        """Test fallback summary generation with no threads."""
        threads = []
        time_period_hours = 24
        
        summary = email_digest_service._generate_fallback_summary(threads, time_period_hours)
        
        assert summary == "No emails received in the last 24 hours."
    
    def test_identify_important_threads_unread(self, email_digest_service, sample_email_thread):
        """Test important thread identification for unread messages."""
        threads = [sample_email_thread]
        
        important = email_digest_service._identify_important_threads(threads)
        
        assert len(important) == 1
        assert important[0].id == "thread123"
    
    def test_identify_important_threads_keywords(self, email_digest_service, sample_email_message):
        """Test important thread identification by keywords."""
        # Create thread with urgent keyword
        urgent_thread = EmailThread(
            id="urgent123",
            subject="URGENT: Important Meeting",
            messages=[sample_email_message],
            participants=["sender@example.com"],
            last_message_date=datetime.now(),
            message_count=1,
            is_unread=False  # Read but has urgent keyword
        )
        
        threads = [urgent_thread]
        important = email_digest_service._identify_important_threads(threads)
        
        assert len(important) == 1
        assert important[0].subject == "URGENT: Important Meeting"
    
    def test_identify_important_threads_multiple_messages(self, email_digest_service, sample_email_message):
        """Test important thread identification by message count."""
        # Create thread with multiple messages
        multi_message_thread = EmailThread(
            id="multi123",
            subject="Regular Subject",
            messages=[sample_email_message, sample_email_message, sample_email_message],
            participants=["sender@example.com"],
            last_message_date=datetime.now(),
            message_count=3,
            is_unread=False
        )
        
        threads = [multi_message_thread]
        important = email_digest_service._identify_important_threads(threads)
        
        assert len(important) == 1
        assert important[0].message_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_digest_success(self, email_digest_service, sample_email_thread):
        """Test successful digest generation."""
        request = EmailDigestRequest(hours_back=24, max_threads=10)
        user_id = "test-user"
        
        # Mock Gmail service responses
        mock_connection = MagicMock()
        email_digest_service.gmail_service.get_connection.return_value = mock_connection
        email_digest_service.gmail_service.get_email_threads.return_value = [sample_email_thread]
        
        digest = await email_digest_service.generate_digest(user_id, request)
        
        assert digest is not None
        assert isinstance(digest, EmailDigestResponse)
        assert digest.thread_count == 1
        assert digest.unread_count == 1
        assert digest.time_period_hours == 24
        assert len(digest.important_threads) == 1
        assert "Test AI summary" in digest.summary
    
    @pytest.mark.asyncio
    async def test_generate_digest_no_connection(self, email_digest_service):
        """Test digest generation when no Gmail connection exists."""
        request = EmailDigestRequest(hours_back=24, max_threads=10)
        user_id = "test-user"
        
        # Mock no connection
        email_digest_service.gmail_service.get_connection.return_value = None
        
        digest = await email_digest_service.generate_digest(user_id, request)
        
        assert digest is None
    
    @pytest.mark.asyncio
    async def test_generate_digest_no_emails(self, email_digest_service):
        """Test digest generation when no emails are found."""
        request = EmailDigestRequest(hours_back=24, max_threads=10)
        user_id = "test-user"
        
        # Mock connection but no emails
        mock_connection = MagicMock()
        email_digest_service.gmail_service.get_connection.return_value = mock_connection
        email_digest_service.gmail_service.get_email_threads.return_value = []
        
        digest = await email_digest_service.generate_digest(user_id, request)
        
        assert digest is not None
        assert digest.thread_count == 0
        assert digest.unread_count == 0
        assert "No emails found" in digest.summary
        assert len(digest.important_threads) == 0
    
    @pytest.mark.asyncio
    async def test_generate_digest_exception(self, email_digest_service):
        """Test digest generation with exception handling."""
        request = EmailDigestRequest(hours_back=24, max_threads=10)
        user_id = "test-user"
        
        # Mock exception
        email_digest_service.gmail_service.get_connection.side_effect = Exception("Test error")
        
        digest = await email_digest_service.generate_digest(user_id, request)
        
        assert digest is None
    
    @pytest.mark.asyncio
    async def test_test_gmail_connection(self, email_digest_service):
        """Test Gmail connection testing."""
        user_id = "test-user"
        
        # Mock successful connection test
        email_digest_service.gmail_service.test_connection.return_value = True
        
        result = await email_digest_service.test_gmail_connection(user_id)
        
        assert result is True
        email_digest_service.gmail_service.test_connection.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_context_manager(self, email_digest_service):
        """Test async context manager functionality."""
        async with email_digest_service as service:
            assert service == email_digest_service
        
        # Verify Gmail service context manager was called
        email_digest_service.gmail_service.__aenter__.assert_called_once()
        email_digest_service.gmail_service.__aexit__.assert_called_once()
    
    def test_llm_interface_initialization_failure(self, mock_db_client):
        """Test handling of LLM interface initialization failure."""
        with patch('chatServer.services.email_digest_service.ConfigLoader', side_effect=Exception("Config error")), \
             patch('chatServer.services.email_digest_service.GmailService'):
            
            service = EmailDigestService(mock_db_client)
            assert service.llm_interface is None
    
    @pytest.mark.asyncio
    async def test_generate_summary_no_llm_interface(self, email_digest_service, sample_email_thread):
        """Test summary generation when LLM interface is not available."""
        threads = [sample_email_thread]
        time_period_hours = 24
        
        # Set LLM interface to None
        email_digest_service.llm_interface = None
        
        summary = await email_digest_service._generate_summary_with_llm(threads, time_period_hours)
        
        # Should fall back to basic summary
        assert "Email Digest - Last 24 hours" in summary
        assert "Total threads: 1" in summary 