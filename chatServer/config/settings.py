"""Settings and environment variable management."""

import os
from typing import Optional
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # Supabase configuration
        self.supabase_jwt_secret: Optional[str] = os.getenv("SUPABASE_JWT_SECRET")
        self.supabase_url: Optional[str] = os.getenv("VITE_SUPABASE_URL")
        self.supabase_service_key: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
        
        # Database configuration
        self.db_user: Optional[str] = os.getenv("SUPABASE_DB_USER")
        self.db_password: Optional[str] = os.getenv("SUPABASE_DB_PASSWORD")
        self.db_host: Optional[str] = os.getenv("SUPABASE_DB_HOST")
        self.db_name: str = os.getenv("SUPABASE_DB_NAME", "postgres")
        self.db_port: str = os.getenv("SUPABASE_DB_PORT", "5432")
        
        # Runtime configuration
        self.running_in_docker: bool = os.getenv("RUNNING_IN_DOCKER") == "true"
        self.llm_agent_src_path: str = os.getenv("LLM_AGENT_SRC_PATH", "src")
        
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
    
    def validate_required_settings(self) -> None:
        """Validate that all required settings are present."""
        errors = []
        
        if not self.supabase_jwt_secret:
            errors.append("SUPABASE_JWT_SECRET is required")
        
        if not self.supabase_url:
            errors.append("VITE_SUPABASE_URL is required")
        
        if not self.supabase_service_key:
            errors.append("SUPABASE_SERVICE_KEY is required")
        
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