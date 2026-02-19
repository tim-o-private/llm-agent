import logging
from typing import Optional

from core.agent_loader_db import load_agent_executor_db
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
    """
    return load_agent_executor_db(
        agent_name=agent_name,
        user_id=user_id,
        session_id=session_id,
        log_level=log_level,
    )
