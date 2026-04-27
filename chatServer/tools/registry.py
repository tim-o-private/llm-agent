"""Tool type registry.

Provides @register_tool_type decorator and get_tool_class lookup.
This module MUST NOT import tool classes at module level to avoid
circular dependencies.
"""

from typing import Type

_registry: dict[str, Type] = {}


def register_tool_type(db_type: str):
    """Decorator that registers a tool class under its database type string."""

    def decorator(cls: Type) -> Type:
        _registry[db_type] = cls
        return cls

    return decorator


def get_tool_class(db_type: str) -> Type | None:
    """Lookup a registered tool class by its database type string."""
    return _registry.get(db_type)
