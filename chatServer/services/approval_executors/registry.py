"""Executor registry — maps card_type strings to executor classes.

Registration happens at import time via the ``@register_executor`` decorator.
The dispatch layer calls ``get_executor(card_type)`` to look up the class.
"""

from __future__ import annotations

from typing import Dict, Type

from . import CardExecutor

EXECUTOR_REGISTRY: Dict[str, Type[CardExecutor]] = {}


def register_executor(card_type: str):
    """Decorator to register an executor for a card_type."""

    def wrapper(cls: Type[CardExecutor]):
        EXECUTOR_REGISTRY[card_type] = cls
        return cls

    return wrapper


def get_executor(card_type: str) -> Type[CardExecutor]:
    """Look up the executor class for a card_type.

    Raises ``KeyError`` if no executor is registered for the type.
    """
    return EXECUTOR_REGISTRY[card_type]
