"""WorkflowCheckpointer — wraps LangGraph's AsyncPostgresSaver.

Manages a psycopg AsyncConnectionPool scoped to the chatServer's
Postgres connection. Pool lifecycle managed in main.py lifespan.
"""

import logging
import os
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


class WorkflowCheckpointer:
    """Manages the Postgres checkpointer lifecycle for workflows."""

    def __init__(self, database_url: str):
        self._db_url = database_url
        self._pool: Optional[AsyncConnectionPool] = None
        self._saver: Optional[AsyncPostgresSaver] = None

    async def setup(self) -> None:
        """Initialize the connection pool and checkpointer tables."""
        self._pool = AsyncConnectionPool(
            self._db_url,
            kwargs={"prepare_threshold": None, "autocommit": True},
            open=False,
        )
        await self._pool.open()
        self._saver = AsyncPostgresSaver(self._pool)
        await self._saver.setup()
        logger.info("WorkflowCheckpointer initialized")

    async def shutdown(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._saver = None
            logger.info("WorkflowCheckpointer shut down")

    @property
    def saver(self) -> AsyncPostgresSaver:
        """Get the checkpointer saver instance."""
        if not self._saver:
            raise RuntimeError("WorkflowCheckpointer not initialized. Call setup() first.")
        return self._saver

    @property
    def is_ready(self) -> bool:
        return self._saver is not None


def _build_database_url() -> str:
    """Build Postgres connection URL from environment variables."""
    host = os.getenv("SUPABASE_DB_HOST", "localhost")
    port = os.getenv("SUPABASE_DB_PORT", "5432")
    name = os.getenv("SUPABASE_DB_NAME", "postgres")
    user = os.getenv("SUPABASE_DB_USER", "postgres")
    password = os.getenv("SUPABASE_DB_PASSWORD", "")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


# -- Global instance management --

_checkpointer: Optional[WorkflowCheckpointer] = None


def get_workflow_checkpointer() -> WorkflowCheckpointer:
    """Get the global WorkflowCheckpointer instance."""
    global _checkpointer
    if _checkpointer is None:
        raise RuntimeError(
            "WorkflowCheckpointer not initialized. "
            "Call initialize_workflow_checkpointer() first."
        )
    return _checkpointer


async def initialize_workflow_checkpointer() -> WorkflowCheckpointer:
    """Initialize the global WorkflowCheckpointer."""
    global _checkpointer
    db_url = _build_database_url()
    _checkpointer = WorkflowCheckpointer(db_url)
    await _checkpointer.setup()
    return _checkpointer


async def shutdown_workflow_checkpointer() -> None:
    """Shut down the global WorkflowCheckpointer."""
    global _checkpointer
    if _checkpointer:
        await _checkpointer.shutdown()
        _checkpointer = None
