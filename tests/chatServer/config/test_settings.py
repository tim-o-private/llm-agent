"""Unit tests for settings module."""

import unittest
from unittest.mock import patch, MagicMock
import os

from chatServer.config.settings import Settings, get_settings


class TestSettings(unittest.TestCase):
    """Test cases for Settings class."""

    def setUp(self):
        """Clear the lru_cache before each test."""
        get_settings.cache_clear()

    def test_settings_with_all_env_vars(self):
        """Test Settings initialization with all environment variables set."""
        env_vars = {
            "SUPABASE_JWT_SECRET": "test_jwt_secret",
            "VITE_SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test_service_key",
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host",
            "SUPABASE_DB_NAME": "test_db",
            "SUPABASE_DB_PORT": "5433",
            "RUNNING_IN_DOCKER": "true",
            "LLM_AGENT_SRC_PATH": "custom_src",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            self.assertEqual(settings.supabase_jwt_secret, "test_jwt_secret")
            self.assertEqual(settings.supabase_url, "https://test.supabase.co")
            self.assertEqual(settings.supabase_service_key, "test_service_key")
            self.assertEqual(settings.db_user, "test_user")
            self.assertEqual(settings.db_password, "test_password")
            self.assertEqual(settings.db_host, "test_host")
            self.assertEqual(settings.db_name, "test_db")
            self.assertEqual(settings.db_port, "5433")
            self.assertTrue(settings.running_in_docker)
            self.assertEqual(settings.llm_agent_src_path, "custom_src")

    def test_settings_with_defaults(self):
        """Test Settings initialization with default values."""
        minimal_env = {
            "SUPABASE_JWT_SECRET": "test_jwt_secret",
            "VITE_SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test_service_key",
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host",
        }
        
        with patch.dict(os.environ, minimal_env, clear=True):
            settings = Settings()
            
            # Check defaults
            self.assertEqual(settings.db_name, "postgres")
            self.assertEqual(settings.db_port, "5432")
            self.assertFalse(settings.running_in_docker)
            self.assertEqual(settings.llm_agent_src_path, "src")

    def test_database_url_property(self):
        """Test the database_url property."""
        env_vars = {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host",
            "SUPABASE_DB_NAME": "test_db",
            "SUPABASE_DB_PORT": "5433",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            expected_url = "postgresql://test_user:test_password@test_host:5433/test_db?connect_timeout=10&sslmode=require"
            self.assertEqual(settings.database_url, expected_url)

    def test_database_url_missing_credentials(self):
        """Test database_url property with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            with self.assertRaises(RuntimeError) as context:
                _ = settings.database_url
            
            self.assertIn("Missing env vars", str(context.exception))
            self.assertIn("SUPABASE_DB_USER", str(context.exception))
            self.assertIn("SUPABASE_DB_PASSWORD", str(context.exception))
            self.assertIn("SUPABASE_DB_HOST", str(context.exception))

    def test_validate_required_settings_success(self):
        """Test validate_required_settings with all required settings."""
        env_vars = {
            "SUPABASE_JWT_SECRET": "test_jwt_secret",
            "VITE_SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test_service_key",
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            # Should not raise any exception
            settings.validate_required_settings()

    def test_validate_required_settings_missing_jwt_secret(self):
        """Test validate_required_settings with missing JWT secret."""
        env_vars = {
            "VITE_SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test_service_key",
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            with self.assertRaises(RuntimeError) as context:
                settings.validate_required_settings()
            
            self.assertIn("SUPABASE_JWT_SECRET is required", str(context.exception))

    def test_validate_required_settings_missing_supabase_url(self):
        """Test validate_required_settings with missing Supabase URL."""
        env_vars = {
            "SUPABASE_JWT_SECRET": "test_jwt_secret",
            "SUPABASE_SERVICE_KEY": "test_service_key",
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            with self.assertRaises(RuntimeError) as context:
                settings.validate_required_settings()
            
            self.assertIn("VITE_SUPABASE_URL is required", str(context.exception))

    def test_cors_origins_default(self):
        """Test that CORS origins are set correctly."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            expected_origins = [
                "https://clarity-webapp.fly.dev",
                "http://localhost:3000"
            ]
            self.assertEqual(settings.cors_origins, expected_origins)


class TestGetSettings(unittest.TestCase):
    """Test cases for get_settings function."""

    def setUp(self):
        """Clear the lru_cache before each test."""
        get_settings.cache_clear()

    def test_get_settings_caching(self):
        """Test that get_settings returns the same instance (caching)."""
        with patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test"}, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()
            
            # Should be the same instance due to lru_cache
            self.assertIs(settings1, settings2)

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        with patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test"}, clear=True):
            settings = get_settings()
            self.assertIsInstance(settings, Settings)


if __name__ == '__main__':
    unittest.main() 