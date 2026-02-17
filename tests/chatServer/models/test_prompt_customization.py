"""Unit tests for prompt customization models."""

import unittest
from datetime import datetime

from pydantic import ValidationError

from chatServer.models.prompt_customization import (
    PromptCustomization,
    PromptCustomizationBase,
    PromptCustomizationCreate,
)


class TestPromptCustomizationBase(unittest.TestCase):
    """Test cases for PromptCustomizationBase model."""

    def test_minimal_prompt_customization_base(self):
        """Test creating a minimal PromptCustomizationBase."""
        customization = PromptCustomizationBase(
            agent_name="test_agent",
            content={"instructions": "Be helpful"}
        )

        self.assertEqual(customization.agent_name, "test_agent")
        self.assertEqual(customization.customization_type, "instruction_set")  # default
        self.assertEqual(customization.content, {"instructions": "Be helpful"})
        self.assertTrue(customization.is_active)  # default
        self.assertEqual(customization.priority, 0)  # default

    def test_full_prompt_customization_base(self):
        """Test creating a PromptCustomizationBase with all fields."""
        content = {
            "instructions": "Be very helpful",
            "tone": "professional",
            "examples": ["example1", "example2"]
        }
        customization = PromptCustomizationBase(
            agent_name="test_agent",
            customization_type="system_prompt",
            content=content,
            is_active=False,
            priority=5
        )

        self.assertEqual(customization.agent_name, "test_agent")
        self.assertEqual(customization.customization_type, "system_prompt")
        self.assertEqual(customization.content, content)
        self.assertFalse(customization.is_active)
        self.assertEqual(customization.priority, 5)

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing agent_name
        with self.assertRaises(ValidationError):
            PromptCustomizationBase(content={"instructions": "Be helpful"})

        # Missing content
        with self.assertRaises(ValidationError):
            PromptCustomizationBase(agent_name="test_agent")

    def test_content_validation(self):
        """Test that content must be a dictionary."""
        # Valid dictionary content
        customization = PromptCustomizationBase(
            agent_name="test_agent",
            content={"key": "value"}
        )
        self.assertEqual(customization.content, {"key": "value"})

        # Invalid content types should raise ValidationError
        with self.assertRaises(ValidationError):
            PromptCustomizationBase(
                agent_name="test_agent",
                content="not a dict"
            )


class TestPromptCustomizationCreate(unittest.TestCase):
    """Test cases for PromptCustomizationCreate model."""

    def test_inherits_from_base(self):
        """Test that PromptCustomizationCreate inherits from base."""
        customization = PromptCustomizationCreate(
            agent_name="test_agent",
            content={"instructions": "Be helpful"}
        )

        # Should have all the same fields as base
        self.assertEqual(customization.agent_name, "test_agent")
        self.assertEqual(customization.customization_type, "instruction_set")
        self.assertEqual(customization.content, {"instructions": "Be helpful"})
        self.assertTrue(customization.is_active)
        self.assertEqual(customization.priority, 0)


class TestPromptCustomization(unittest.TestCase):
    """Test cases for PromptCustomization model."""

    def test_full_prompt_customization(self):
        """Test creating a full PromptCustomization with all fields."""
        now = datetime.now()
        customization = PromptCustomization(
            agent_name="test_agent",
            content={"instructions": "Be helpful"},
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="987fcdeb-51a2-43d1-9f12-345678901234",
            created_at=now,
            updated_at=now
        )

        self.assertEqual(customization.agent_name, "test_agent")
        self.assertEqual(customization.content, {"instructions": "Be helpful"})
        self.assertEqual(customization.id, "123e4567-e89b-12d3-a456-426614174000")
        self.assertEqual(customization.user_id, "987fcdeb-51a2-43d1-9f12-345678901234")
        self.assertEqual(customization.created_at, now)
        self.assertEqual(customization.updated_at, now)

    def test_missing_additional_required_fields(self):
        """Test that missing id and user_id raise ValidationError."""
        # Missing id
        with self.assertRaises(ValidationError):
            PromptCustomization(
                agent_name="test_agent",
                content={"instructions": "Be helpful"},
                user_id="987fcdeb-51a2-43d1-9f12-345678901234",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

        # Missing user_id
        with self.assertRaises(ValidationError):
            PromptCustomization(
                agent_name="test_agent",
                content={"instructions": "Be helpful"},
                id="123e4567-e89b-12d3-a456-426614174000",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

    def test_datetime_fields(self):
        """Test that datetime fields accept various formats."""
        # Test with datetime objects
        now = datetime.now()
        customization = PromptCustomization(
            agent_name="test_agent",
            content={"instructions": "Be helpful"},
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="987fcdeb-51a2-43d1-9f12-345678901234",
            created_at=now,
            updated_at=now
        )
        self.assertEqual(customization.created_at, now)
        self.assertEqual(customization.updated_at, now)

        # Test with string representations (common from database)
        customization_str = PromptCustomization(
            agent_name="test_agent",
            content={"instructions": "Be helpful"},
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="987fcdeb-51a2-43d1-9f12-345678901234",
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:00:00"
        )
        self.assertEqual(customization_str.created_at, "2023-01-01T12:00:00")
        self.assertEqual(customization_str.updated_at, "2023-01-01T12:00:00")


if __name__ == '__main__':
    unittest.main()
