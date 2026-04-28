"""Tests for the tool type registry."""

import pytest

from chatServer.tools.registry import _registry, get_tool_class, register_tool_type


@pytest.fixture(autouse=True)
def isolate_registry():
    """Save and restore _registry state around each test."""
    original = dict(_registry)
    yield
    _registry.clear()
    _registry.update(original)


class _DummyClassA:
    pass


class _DummyClassB:
    pass


class TestRegisterToolType:
    """Tests for @register_tool_type decorator and get_tool_class lookup."""

    def test_register_tool_type_decorator(self):
        """Decorating a class registers it in _registry."""
        type_key = "TestRegistryToolA"

        @register_tool_type(type_key)
        class DummyClass:
            pass

        assert type_key in _registry
        assert _registry[type_key] is DummyClass

    def test_get_tool_class_existing(self):
        """Lookup returns the correct class for a registered type."""
        type_key = "TestRegistryToolB"
        _registry[type_key] = _DummyClassA

        result = get_tool_class(type_key)
        assert result is _DummyClassA

    def test_get_tool_class_missing(self):
        """Lookup returns None for unregistered type."""
        result = get_tool_class("NonExistentToolTypeXYZ")
        assert result is None

    def test_register_overwrite(self):
        """Registering the same type string twice overwrites with the latest class."""
        type_key = "TestRegistryToolC"

        @register_tool_type(type_key)
        class FirstClass:
            pass

        assert _registry[type_key] is FirstClass

        @register_tool_type(type_key)
        class SecondClass:
            pass

        assert _registry[type_key] is SecondClass
