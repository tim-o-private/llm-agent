"""Database management for the chat server."""

from .connection import DatabaseManager, get_db_connection
from .scoped_client import SystemClient, UserScopedClient
from .supabase_client import (
    SupabaseManager,
    create_system_client,
    create_user_scoped_client,
    get_supabase_client,
    get_system_client,
    get_user_scoped_client,
)
from .user_scoped_tables import USER_SCOPED_TABLES

__all__ = [
    "DatabaseManager",
    "get_db_connection",
    "SupabaseManager",
    "create_system_client",
    "create_user_scoped_client",
    "get_supabase_client",
    "get_system_client",
    "get_user_scoped_client",
    "SystemClient",
    "UserScopedClient",
    "USER_SCOPED_TABLES",
]
