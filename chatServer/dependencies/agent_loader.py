"""Agent loader dependency."""

from src.core import agent_loader_db as agent_loader


def get_agent_loader():
    """Dependency for agent loader - can be overridden in tests."""
    return agent_loader
