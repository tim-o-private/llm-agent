"""Settings and environment variable management."""

import os
from functools import lru_cache
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Supabase configuration
        self.supabase_jwt_secret: Optional[str] = os.getenv("SUPABASE_JWT_SECRET")
        self.supabase_url: Optional[str] = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
        self.supabase_service_key: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

        # Database configuration
        self.db_user: Optional[str] = os.getenv("SUPABASE_DB_USER")
        self.db_password: Optional[str] = os.getenv("SUPABASE_DB_PASSWORD")
        self.db_host: Optional[str] = os.getenv("SUPABASE_DB_HOST")
        self.db_name: str = os.getenv("SUPABASE_DB_NAME", "postgres")
        self.db_port: str = os.getenv("SUPABASE_DB_PORT", "5432")

        # Runtime configuration
        self.running_in_docker: bool = os.getenv("RUNNING_IN_DOCKER") == "true"
        self.llm_agent_src_path: str = os.getenv("LLM_AGENT_SRC_PATH", "src")

        # Telegram bot (optional — if not set, Telegram features are disabled)
        self.telegram_bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_webhook_url: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL")

        # CORS origins
        self.cors_origins = [
            "https://clarity-webapp.fly.dev",
            "http://localhost:3000"
        ]

    @property
    def database_url(self) -> str:
        """Get the database connection string."""
        if not all([self.db_user, self.db_password, self.db_host]):
            missing = []
            if not self.db_user:
                missing.append("SUPABASE_DB_USER")
            if not self.db_password:
                missing.append("SUPABASE_DB_PASSWORD")
            if not self.db_host:
                missing.append("SUPABASE_DB_HOST")
            raise RuntimeError(f"Database connection cannot be initialized. Missing env vars: {missing}")

        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?connect_timeout=10&sslmode=require"

    def reload_from_env(self) -> None:
        """Re-read all settings from environment variables.

        Call this after load_dotenv() to pick up values that weren't in the
        shell environment at import time (e.g. TELEGRAM_BOT_TOKEN added to .env).
        """
        self.supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        self.supabase_url = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db_user = os.getenv("SUPABASE_DB_USER")
        self.db_password = os.getenv("SUPABASE_DB_PASSWORD")
        self.db_host = os.getenv("SUPABASE_DB_HOST")
        self.db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
        self.db_port = os.getenv("SUPABASE_DB_PORT", "5432")
        self.running_in_docker = os.getenv("RUNNING_IN_DOCKER") == "true"
        self.llm_agent_src_path = os.getenv("LLM_AGENT_SRC_PATH", "src")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")

    def validate_required_settings(self) -> None:
        """Validate that all required settings are present."""
        errors = []

        if not self.supabase_jwt_secret:
            errors.append("SUPABASE_JWT_SECRET is required")

        if not self.supabase_url:
            errors.append("SUPABASE_URL is required")

        if not self.supabase_service_key:
            errors.append("SUPABASE_SERVICE_ROLE_KEY is required")

        # Database settings are validated in database_url property
        try:
            _ = self.database_url
        except RuntimeError as e:
            errors.append(str(e))

        if errors:
            raise RuntimeError(f"Configuration validation failed: {'; '.join(errors)}")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
