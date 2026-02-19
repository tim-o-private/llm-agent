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
        )

        self.assertEqual(customization.agent_name, "test_agent")
        self.assertEqual(customization.instructions, "")  # default
        self.assertTrue(customization.is_active)  # default

    def test_full_prompt_customization_base(self):
        """Test creating a PromptCustomizationBase with all fields."""
        customization = PromptCustomizationBase(
            agent_name="test_agent",
            instructions="Always respond in bullet points. Be concise.",
            is_active=False,
        )

        self.assertEqual(customization.agent_name, "test_agent")
        self.assertEqual(customization.instructions, "Always respond in bullet points. Be concise.")
        self.assertFalse(customization.is_active)

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing agent_name
        with self.assertRaises(ValidationError):
            PromptCustomizationBase()

    def test_instructions_is_text(self):
        """Test that instructions is a plain text field."""
        customization = PromptCustomizationBase(
            agent_name="test_agent",
            instructions="Use bullet points for all responses."
        )
        self.assertEqual(customization.instructions, "Use bullet points for all responses.")


class TestPromptCustomizationCreate(unittest.TestCase):
    """Test cases for PromptCustomizationCreate model."""

    def test_inherits_from_base(self):
        """Test that PromptCustomizationCreate inherits from base."""
        customization = PromptCustomizationCreate(
            agent_name="test_agent",
            instructions="Be helpful"
        )

        self.assertEqual(customization.agent_name, "test_agent")
        self.assertEqual(customization.instructions, "Be helpful")
        self.assertTrue(customization.is_active)


class TestPromptCustomization(unittest.TestCase):
    """Test cases for PromptCustomization model."""

    def test_full_prompt_customization(self):
        """Test creating a full PromptCustomization with all fields."""
        now = datetime.now()
        customization = PromptCustomization(
            agent_name="test_agent",
            instructions="Be helpful",
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="987fcdeb-51a2-43d1-9f12-345678901234",
            created_at=now,
            updated_at=now
        )

        self.assertEqual(customization.agent_name, "test_agent")
        self.assertEqual(customization.instructions, "Be helpful")
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
                instructions="Be helpful",
                user_id="987fcdeb-51a2-43d1-9f12-345678901234",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

        # Missing user_id
        with self.assertRaises(ValidationError):
            PromptCustomization(
                agent_name="test_agent",
                instructions="Be helpful",
                id="123e4567-e89b-12d3-a456-426614174000",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

    def test_datetime_fields(self):
        """Test that datetime fields accept various formats."""
        now = datetime.now()
        customization = PromptCustomization(
            agent_name="test_agent",
            instructions="Be helpful",
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
            instructions="Be helpful",
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="987fcdeb-51a2-43d1-9f12-345678901234",
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:00:00"
        )
        self.assertEqual(customization_str.created_at, "2023-01-01T12:00:00")
        self.assertEqual(customization_str.updated_at, "2023-01-01T12:00:00")


if __name__ == '__main__':
    unittest.main()
