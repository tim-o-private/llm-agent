import logging
from typing import Optional

from core.agent_loader_db import load_agent_executor_db, load_agent_executor_db_async
from core.agents.customizable_agent import CustomizableAgentExecutor
from utils.logging_utils import get_logger

logger = get_logger(__name__)

def load_agent_executor(
    agent_name: str,
    user_id: str,
    session_id: str,
    config_loader=None,  # Deprecated, ignored
    log_level: int = logging.INFO,
    ltm_notes: Optional[str] = None,  # Deprecated, ignored
) -> CustomizableAgentExecutor:
    """
    Loads agent configuration and tools from the database, instantiates the agent executor.
    Sync version — kept for backward compatibility and CLI usage.
    """
    return load_agent_executor_db(
        agent_name=agent_name,
        user_id=user_id,
        session_id=session_id,
        log_level=log_level,
    )


async def async_load_agent_executor(
    agent_name: str,
    user_id: str,
    session_id: str,
    log_level: int = logging.INFO,
    channel: str = "web",
) -> CustomizableAgentExecutor:
    """Async version — non-blocking, uses cached configs, parallelizes DB calls."""
    return await load_agent_executor_db_async(
        agent_name=agent_name,
        user_id=user_id,
        session_id=session_id,
        log_level=log_level,
        channel=channel,
    )
