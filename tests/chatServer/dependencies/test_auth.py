"""Unit tests for auth dependencies."""

import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, Request
import os
import pytest

from chatServer.dependencies.auth import get_current_user, get_jwt_from_request_context


class TestGetCurrentUser(unittest.TestCase):
    """Test cases for get_current_user function."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the settings cache before each test
        from chatServer.config.settings import get_settings
        get_settings.cache_clear()

    def test_get_current_user_success(self):
        """Test successful user extraction from valid JWT."""
        # Mock a valid JWT payload
        mock_payload = {"sub": "user123", "aud": "authenticated"}
        
        with patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test_secret"}, clear=True):
            with patch('chatServer.dependencies.auth.jwt.decode', return_value=mock_payload):
                # Create a mock request with valid authorization header
                mock_request = MagicMock(spec=Request)
                mock_request.headers.get.return_value = "Bearer valid_token"
                
                # Suppress print statements for cleaner test output
                with patch('builtins.print'):
                    user_id = get_current_user(mock_request)
                
                self.assertEqual(user_id, "user123")

    def test_get_current_user_missing_auth_header(self):
        """Test error when authorization header is missing."""
        with patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test_secret"}, clear=True):
            mock_request = MagicMock(spec=Request)
            mock_request.headers.get.return_value = None
            
            with self.assertRaises(HTTPException) as context:
                get_current_user(mock_request)
            
            self.assertEqual(context.exception.status_code, 401)
            self.assertIn("Missing or invalid authorization header", context.exception.detail)

    def test_get_current_user_invalid_auth_header_format(self):
        """Test error when authorization header doesn't start with 'Bearer '."""
        with patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test_secret"}, clear=True):
            mock_request = MagicMock(spec=Request)
            mock_request.headers.get.return_value = "Invalid token_here"
            
            with self.assertRaises(HTTPException) as context:
                get_current_user(mock_request)
            
            self.assertEqual(context.exception.status_code, 401)
            self.assertIn("Missing or invalid authorization header", context.exception.detail)

    def test_get_current_user_jwt_decode_error(self):
        """Test error when JWT decoding fails."""
        from jose import JWTError
        
        with patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test_secret"}, clear=True):
            with patch('chatServer.dependencies.auth.jwt.decode', side_effect=JWTError("Invalid token")):
                mock_request = MagicMock(spec=Request)
                mock_request.headers.get.return_value = "Bearer invalid_token"
                
                with patch('builtins.print'):  # Suppress print statements
                    with self.assertRaises(HTTPException) as context:
                        get_current_user(mock_request)
                
                self.assertEqual(context.exception.status_code, 401)
                self.assertEqual(context.exception.detail, "Invalid token")

    def test_get_current_user_missing_user_id_in_payload(self):
        """Test error when JWT payload doesn't contain user ID."""
        mock_payload = {"aud": "authenticated"}  # Missing 'sub' field
        
        with patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test_secret"}, clear=True):
            with patch('chatServer.dependencies.auth.jwt.decode', return_value=mock_payload):
                mock_request = MagicMock(spec=Request)
                mock_request.headers.get.return_value = "Bearer valid_token"
                
                with patch('builtins.print'):  # Suppress print statements
                    with self.assertRaises(HTTPException) as context:
                        get_current_user(mock_request)
                
                self.assertEqual(context.exception.status_code, 401)
                self.assertEqual(context.exception.detail, "User ID not found in token")

    def test_get_current_user_empty_user_id(self):
        """Test error when user ID in JWT payload is empty."""
        mock_payload = {"sub": "", "aud": "authenticated"}  # Empty user ID
        
        with patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test_secret"}, clear=True):
            with patch('chatServer.dependencies.auth.jwt.decode', return_value=mock_payload):
                mock_request = MagicMock(spec=Request)
                mock_request.headers.get.return_value = "Bearer valid_token"
                
                with patch('builtins.print'):  # Suppress print statements
                    with self.assertRaises(HTTPException) as context:
                        get_current_user(mock_request)
                
                self.assertEqual(context.exception.status_code, 401)
                self.assertEqual(context.exception.detail, "User ID not found in token")


class TestGetJwtFromRequestContext:
    """Test cases for get_jwt_from_request_context function."""

    @pytest.mark.asyncio
    async def test_get_jwt_from_request_context_success(self):
        """Test successful JWT extraction from request."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "Bearer test_token_123"
        
        token = await get_jwt_from_request_context(mock_request)
        
        assert token == "test_token_123"

    @pytest.mark.asyncio
    async def test_get_jwt_from_request_context_missing_header(self):
        """Test JWT extraction when authorization header is missing."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = None
        
        token = await get_jwt_from_request_context(mock_request)
        
        assert token is None

    @pytest.mark.asyncio
    async def test_get_jwt_from_request_context_invalid_format(self):
        """Test JWT extraction when authorization header has invalid format."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "Invalid token_format"
        
        token = await get_jwt_from_request_context(mock_request)
        
        assert token is None

    @pytest.mark.asyncio
    async def test_get_jwt_from_request_context_empty_header(self):
        """Test JWT extraction when authorization header is empty."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = ""
        
        token = await get_jwt_from_request_context(mock_request)
        
        assert token is None

    @pytest.mark.asyncio
    async def test_get_jwt_from_request_context_bearer_only(self):
        """Test JWT extraction when authorization header only contains 'Bearer'."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "Bearer"
        
        token = await get_jwt_from_request_context(mock_request)
        
        assert token is None 