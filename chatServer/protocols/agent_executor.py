"""Protocol definition for agent executors."""

from typing import Any, Dict, Optional, Protocol


class AgentExecutorProtocol(Protocol):
    """Protocol defining the interface we expect from agent executors."""
    memory: Any  # The memory system

    async def ainvoke(self, inputs: Dict[str, Any], config: Optional[Any] = None) -> Dict[str, Any]:
        """Asynchronously invoke the agent with inputs."""
        ...
