"""Default service registry for workflow nodes.

Future service nodes (e.g. notify, schedule, external API calls) can be
registered here and picked up automatically by WorkflowRunManager.
"""

from typing import Any, Callable, Coroutine

from .nodes.deliver_briefing import deliver_briefing

DEFAULT_SERVICE_REGISTRY: dict[str, Callable[..., Coroutine[Any, Any, str]]] = {
    "deliver": deliver_briefing,
}
