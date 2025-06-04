"""Gmail API service for email integration."""
# @docs memory-bank/patterns/api-patterns.md#pattern-3-service-layer-pattern
# @rules memory-bank/rules/api-rules.json#api-003

import base64
import email
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from supabase import AsyncClient

try:
    from .base_api_service import BaseAPIService, RateLimitInfo
    from ..models.external_api import (
        ServiceName, ExternalAPIConnectionResponse, 
        EmailMessage, EmailThread, EmailDigestRequest
    )
except ImportError:
    from chatServer.services.base_api_service import BaseAPIService, RateLimitInfo
    from chatServer.models.external_api import (
        ServiceName, ExternalAPIConnectionResponse,
        EmailMessage, EmailThread, EmailDigestRequest
    )

logger = logging.getLogger(__name__)


class GmailService(BaseAPIService):
    """Gmail API service for email operations."""
    
    def __init__(self, db_client: AsyncClient = None):
        """Initialize Gmail service.
        
        Args:
            db_client: Supabase client for database operations (optional for direct token usage)
        """
        if db_client:
            super().__init__(db_client, ServiceName.GMAIL)
        else:
            # Initialize without database client for direct token usage
            self.db_client = None
            self.service_name = ServiceName.GMAIL
            self._user_tokens = {}  # Store tokens directly
        
        # Gmail API rate limits (per user)
        # https://developers.google.com/gmail/api/reference/quota
        self.default_rate_limits = RateLimitInfo(
            requests_per_minute=250,  # Gmail allows 250 requests/minute
            requests_per_hour=15000,  # 250 * 60 = 15,000 per hour
            requests_per_day=1000000000  # 1 billion requests per day (effectively unlimited)
        )
        
        self.base_url = "https://gmail.googleapis.com/gmail/v1"
    
    def set_user_tokens(self, user_id: str, access_token: str, refresh_token: str = None):
        """Set OAuth tokens directly for a user (bypasses database).
        
        Args:
            user_id: User ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
        """
        self._user_tokens[user_id] = {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        logger.debug(f"Set tokens for user {user_id}")
    
    async def _get_auth_headers_direct(self, user_id: str) -> Dict[str, str]:
        """Get authentication headers using directly set tokens.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of authentication headers
            
        Raises:
            ValueError: If no tokens are set for the user
        """
        if user_id not in self._user_tokens:
            raise ValueError(f"No tokens set for user {user_id}")
        
        access_token = self._user_tokens[user_id]['access_token']
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def _get_auth_headers(self, connection: ExternalAPIConnectionResponse) -> Dict[str, str]:
        """Get authentication headers for Gmail API requests.
        
        Args:
            connection: API connection with tokens
            
        Returns:
            Dictionary of authentication headers
        """
        return {
            "Authorization": f"Bearer {connection.access_token}",
            "Content-Type": "application/json"
        }
    
    async def get_message(self, user_id: str, message_id: str) -> Optional[Dict]:
        """Get detailed information about a specific message (direct token version).
        
        Args:
            user_id: User ID
            message_id: Gmail message ID
            
        Returns:
            Message details or None if failed
        """
        try:
            url = f"{self.base_url}/users/me/messages/{message_id}"
            params = {"format": "full"}
            
            # Use direct tokens if available, otherwise fall back to database
            if hasattr(self, '_user_tokens') and user_id in self._user_tokens:
                headers = await self._get_auth_headers_direct(user_id)
                
                # Make direct HTTP request (simplified version)
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        logger.error(f"Gmail API error: {response.status_code} - {response.text}")
                        return None
            else:
                # Fall back to original method with database
                return await self.get_message_details(user_id, message_id)
                
        except Exception as e:
            logger.error(f"Failed to get message {message_id} for user {user_id}: {e}")
            return None
    
    async def refresh_token(self, user_id: str, connection: ExternalAPIConnectionResponse) -> bool:
        """Refresh OAuth token for Gmail connection.
        
        Args:
            user_id: User ID
            connection: Current API connection
            
        Returns:
            True if refresh successful, False otherwise
        """
        if not connection.refresh_token:
            logger.error(f"No refresh token available for user {user_id}")
            return False
        
        try:
            # Google OAuth2 token refresh endpoint
            refresh_url = "https://oauth2.googleapis.com/token"
            refresh_data = {
                "client_id": "YOUR_CLIENT_ID",  # TODO: Add to settings
                "client_secret": "YOUR_CLIENT_SECRET",  # TODO: Add to settings
                "refresh_token": connection.refresh_token,
                "grant_type": "refresh_token"
            }
            
            response = await self.http_client.post(refresh_url, data=refresh_data)
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Update tokens in database
                success = await self.update_tokens(
                    user_id, new_access_token, expires_at=expires_at
                )
                
                if success:
                    logger.info(f"Successfully refreshed Gmail token for user {user_id}")
                    return True
                else:
                    logger.error(f"Failed to update refreshed token for user {user_id}")
                    return False
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing Gmail token for user {user_id}: {e}")
            return False
    
    async def test_connection(self, user_id: str) -> bool:
        """Test if the Gmail connection is working.
        
        Args:
            user_id: User ID
            
        Returns:
            True if connection is working, False otherwise
        """
        try:
            # Test with a simple profile request
            url = f"{self.base_url}/users/me/profile"
            response = await self.make_request(user_id, "GET", url, cache_ttl=300)
            return response is not None
        except Exception as e:
            logger.error(f"Gmail connection test failed for user {user_id}: {e}")
            return False
    
    async def get_messages(self, user_id: str, query: str = "", 
                          max_results: int = 20, page_token: Optional[str] = None) -> Optional[Dict]:
        """Get messages from Gmail using search query (direct token version).
        
        Args:
            user_id: User ID
            query: Gmail search query (e.g., "is:unread", "from:example@gmail.com")
            max_results: Maximum number of messages to return
            page_token: Token for pagination
            
        Returns:
            Gmail messages response or None if failed
        """
        try:
            url = f"{self.base_url}/users/me/messages"
            params = {
                "q": query,
                "maxResults": min(max_results, 500)  # Gmail API limit
            }
            if page_token:
                params["pageToken"] = page_token
            
            # Use direct tokens if available, otherwise fall back to database
            if hasattr(self, '_user_tokens') and user_id in self._user_tokens:
                headers = await self._get_auth_headers_direct(user_id)
                
                # Make direct HTTP request (simplified version)
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        logger.error(f"Gmail API error: {response.status_code} - {response.text}")
                        return None
            else:
                # Fall back to original method with database
                url = f"{self.base_url}/users/me/messages"
                params = {
                    "q": query,
                    "maxResults": min(max_results, 500)  # Gmail API limit
                }
                if page_token:
                    params["pageToken"] = page_token
                
                return await self.make_request(user_id, "GET", url, params=params, cache_ttl=300)
                
        except Exception as e:
            logger.error(f"Failed to get messages for user {user_id}: {e}")
            return None
    
    async def get_message_details(self, user_id: str, message_id: str) -> Optional[Dict]:
        """Get detailed information about a specific message.
        
        Args:
            user_id: User ID
            message_id: Gmail message ID
            
        Returns:
            Message details or None if failed
        """
        url = f"{self.base_url}/users/me/messages/{message_id}"
        params = {"format": "full"}
        
        return await self.make_request(user_id, "GET", url, params=params, cache_ttl=600)
    
    async def get_thread_details(self, user_id: str, thread_id: str) -> Optional[Dict]:
        """Get detailed information about a specific thread.
        
        Args:
            user_id: User ID
            thread_id: Gmail thread ID
            
        Returns:
            Thread details or None if failed
        """
        url = f"{self.base_url}/users/me/threads/{thread_id}"
        params = {"format": "full"}
        
        return await self.make_request(user_id, "GET", url, params=params, cache_ttl=600)
    
    def _parse_message_headers(self, headers: List[Dict]) -> Dict[str, str]:
        """Parse message headers into a dictionary.
        
        Args:
            headers: List of header dictionaries from Gmail API
            
        Returns:
            Dictionary of header name -> value
        """
        header_dict = {}
        for header in headers:
            header_dict[header["name"].lower()] = header["value"]
        return header_dict
    
    def _decode_message_body(self, payload: Dict) -> str:
        """Decode message body from Gmail API payload.
        
        Args:
            payload: Message payload from Gmail API
            
        Returns:
            Decoded message body text
        """
        body = ""
        
        if "parts" in payload:
            # Multipart message
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part["body"]:
                    body_data = part["body"]["data"]
                    body += base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                elif part["mimeType"] == "text/html" and not body and "data" in part["body"]:
                    # Fallback to HTML if no plain text
                    body_data = part["body"]["data"]
                    body += base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
        else:
            # Single part message
            if payload["mimeType"] == "text/plain" and "data" in payload["body"]:
                body_data = payload["body"]["data"]
                body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
            elif payload["mimeType"] == "text/html" and "data" in payload["body"]:
                body_data = payload["body"]["data"]
                body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
        
        return body.strip()
    
    def _parse_email_message(self, message_data: Dict) -> EmailMessage:
        """Parse Gmail API message data into EmailMessage model.
        
        Args:
            message_data: Message data from Gmail API
            
        Returns:
            Parsed EmailMessage object
        """
        headers = self._parse_message_headers(message_data["payload"]["headers"])
        body = self._decode_message_body(message_data["payload"])
        
        # Parse date
        date_str = headers.get("date", "")
        try:
            date = email.utils.parsedate_to_datetime(date_str)
        except:
            date = datetime.now()
        
        # Extract labels
        labels = message_data.get("labelIds", [])
        is_read = "UNREAD" not in labels
        
        return EmailMessage(
            id=message_data["id"],
            thread_id=message_data["threadId"],
            subject=headers.get("subject", ""),
            sender=headers.get("from", ""),
            recipient=headers.get("to", ""),
            body=body,
            date=date,
            is_read=is_read,
            labels=labels
        )
    
    async def get_recent_emails(self, user_id: str, request: EmailDigestRequest) -> List[EmailMessage]:
        """Get recent emails for digest generation.
        
        Args:
            user_id: User ID
            request: Email digest request parameters
            
        Returns:
            List of recent email messages
        """
        # Build query for recent emails
        since_date = datetime.now() - timedelta(hours=request.hours_back)
        date_str = since_date.strftime("%Y/%m/%d")
        
        query_parts = [f"after:{date_str}"]
        if not request.include_read:
            query_parts.append("is:unread")
        
        query = " ".join(query_parts)
        
        # Get message list
        messages_response = await self.get_messages(
            user_id, query=query, max_results=request.max_threads
        )
        
        if not messages_response or "messages" not in messages_response:
            return []
        
        # Get detailed information for each message
        email_messages = []
        for message_info in messages_response["messages"]:
            message_details = await self.get_message_details(user_id, message_info["id"])
            if message_details:
                try:
                    email_message = self._parse_email_message(message_details)
                    email_messages.append(email_message)
                except Exception as e:
                    logger.error(f"Error parsing message {message_info['id']}: {e}")
                    continue
        
        # Sort by date (newest first)
        email_messages.sort(key=lambda x: x.date, reverse=True)
        
        return email_messages
    
    async def get_email_threads(self, user_id: str, request: EmailDigestRequest) -> List[EmailThread]:
        """Get email threads for digest generation.
        
        Args:
            user_id: User ID
            request: Email digest request parameters
            
        Returns:
            List of email threads
        """
        # Get recent emails
        recent_emails = await self.get_recent_emails(user_id, request)
        
        # Group emails by thread
        threads_dict = {}
        for email_msg in recent_emails:
            thread_id = email_msg.thread_id
            if thread_id not in threads_dict:
                threads_dict[thread_id] = []
            threads_dict[thread_id].append(email_msg)
        
        # Convert to EmailThread objects
        email_threads = []
        for thread_id, messages in threads_dict.items():
            # Sort messages by date
            messages.sort(key=lambda x: x.date)
            
            # Get thread subject (from first message)
            subject = messages[0].subject if messages else ""
            
            # Get all participants
            participants = set()
            for msg in messages:
                if msg.sender:
                    participants.add(msg.sender)
                if msg.recipient:
                    participants.add(msg.recipient)
            
            # Check if thread has unread messages
            is_unread = any(not msg.is_read for msg in messages)
            
            thread = EmailThread(
                id=thread_id,
                subject=subject,
                messages=messages,
                participants=list(participants),
                last_message_date=messages[-1].date if messages else datetime.now(),
                message_count=len(messages),
                is_unread=is_unread
            )
            email_threads.append(thread)
        
        # Sort threads by last message date (newest first)
        email_threads.sort(key=lambda x: x.last_message_date, reverse=True)
        
        return email_threads[:request.max_threads] 