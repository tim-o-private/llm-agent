"""Settings and environment variable management."""

import os
from typing import Optional, List
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings for Clarity v2 router
    
    This class manages all configuration settings for the router,
    including database connections, API keys, and service URLs.
    """
    
    # Supabase configuration
    SUPABASE_URL: str = Field(
        default="https://dsyakikfxlhjszyhlmaa.supabase.co",
        env="VITE_SUPABASE_URL",
        description="Supabase project URL"
    )
    
    SUPABASE_ANON_KEY: Optional[str] = Field(
        default=None,
        env="VITE_SUPABASE_ANON_KEY",
        description="Supabase anonymous key"
    )
    
    SUPABASE_SERVICE_KEY: Optional[str] = Field(
        default=None,
        env="SUPABASE_SERVICE_KEY",
        description="Supabase service key for server-side operations"
    )
    
    # PostgREST configuration
    @property
    def POSTGREST_URL(self) -> str:
        """PostgREST API URL derived from Supabase URL"""
        return f"{self.SUPABASE_URL}/rest/v1"
    
    # CORS configuration
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
        env="CORS_ORIGINS",
        description="Allowed CORS origins"
    )
    
    # Router configuration
    ROUTER_HOST: str = Field(
        default="0.0.0.0",
        env="ROUTER_HOST",
        description="Router host address"
    )
    
    ROUTER_PORT: int = Field(
        default=8000,
        env="ROUTER_PORT",
        description="Router port"
    )
    
    # Logging configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    
    # AI/LLM configuration
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="OpenAI API key for LLM operations"
    )
    
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        env="GEMINI_API_KEY",
        description="Google Gemini API key for LLM operations"
    )
    
    # Google OAuth configuration (for Gmail tools)
    GOOGLE_CLIENT_ID: Optional[str] = Field(
        default=None,
        env="GOOGLE_CLIENT_ID",
        description="Google OAuth client ID"
    )
    
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        env="GOOGLE_CLIENT_SECRET",
        description="Google OAuth client secret"
    )
    
    # Development settings
    DEBUG: bool = Field(
        default=False,
        env="DEBUG",
        description="Enable debug mode"
    )
    
    DEVELOPMENT_MODE: bool = Field(
        default=True,
        env="DEVELOPMENT_MODE",
        description="Enable development mode features"
    )
    
    # Docker environment detection
    running_in_docker: bool = Field(
        default=False,
        env="RUNNING_IN_DOCKER",
        description="Whether the application is running in Docker"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra environment variables
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Parse CORS origins if provided as string
        if isinstance(self.ALLOWED_ORIGINS, str):
            self.ALLOWED_ORIGINS = [
                origin.strip() 
                for origin in self.ALLOWED_ORIGINS.split(",")
                if origin.strip()
            ]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.DEBUG and not self.DEVELOPMENT_MODE
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        # For PostgREST, we use the REST API URL
        return self.POSTGREST_URL
    
    def validate_required_settings(self) -> List[str]:
        """
        Validate that required settings are present
        
        Returns:
            List of missing required settings
        """
        missing = []
        
        if not self.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        
        if not self.SUPABASE_ANON_KEY and not self.SUPABASE_SERVICE_KEY:
            missing.append("SUPABASE_ANON_KEY or SUPABASE_SERVICE_KEY")
        
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        
        return missing


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    
    This function uses LRU cache to ensure settings are loaded only once
    and reused throughout the application lifecycle.
    """
    return Settings()

# Convenience function to get specific setting values
def get_supabase_url() -> str:
    """Get Supabase URL"""
    return get_settings().SUPABASE_URL

def get_postgrest_url() -> str:
    """Get PostgREST URL"""
    return get_settings().POSTGREST_URL

def get_cors_origins() -> List[str]:
    """Get CORS origins"""
    return get_settings().ALLOWED_ORIGINS

def is_development_mode() -> bool:
    """Check if in development mode"""
    return get_settings().DEVELOPMENT_MODE 