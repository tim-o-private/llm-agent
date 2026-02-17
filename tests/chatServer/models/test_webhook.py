"""Unit tests for webhook models."""

import unittest

from pydantic import ValidationError

from chatServer.models.webhook import SupabasePayload


class TestSupabasePayload(unittest.TestCase):
    """Test cases for SupabasePayload model."""

    def test_minimal_supabase_payload(self):
        """Test creating a minimal SupabasePayload."""
        payload = SupabasePayload(
            type="INSERT",
            table="tasks"
        )

        self.assertEqual(payload.type, "INSERT")
        self.assertEqual(payload.table, "tasks")
        self.assertIsNone(payload.record)
        self.assertIsNone(payload.old_record)
        self.assertIsNone(payload.webhook_schema)

    def test_full_supabase_payload(self):
        """Test creating a SupabasePayload with all fields."""
        record = {"id": 1, "name": "Test Task", "completed": False}
        old_record = {"id": 1, "name": "Old Task", "completed": True}

        payload = SupabasePayload(
            type="UPDATE",
            table="tasks",
            record=record,
            old_record=old_record,
            webhook_schema="public"
        )

        self.assertEqual(payload.type, "UPDATE")
        self.assertEqual(payload.table, "tasks")
        self.assertEqual(payload.record, record)
        self.assertEqual(payload.old_record, old_record)
        self.assertEqual(payload.webhook_schema, "public")

    def test_insert_payload(self):
        """Test creating an INSERT payload."""
        record = {"id": 1, "name": "New Task", "completed": False}

        payload = SupabasePayload(
            type="INSERT",
            table="tasks",
            record=record
        )

        self.assertEqual(payload.type, "INSERT")
        self.assertEqual(payload.table, "tasks")
        self.assertEqual(payload.record, record)
        self.assertIsNone(payload.old_record)  # No old record for INSERT

    def test_delete_payload(self):
        """Test creating a DELETE payload."""
        old_record = {"id": 1, "name": "Deleted Task", "completed": True}

        payload = SupabasePayload(
            type="DELETE",
            table="tasks",
            old_record=old_record
        )

        self.assertEqual(payload.type, "DELETE")
        self.assertEqual(payload.table, "tasks")
        self.assertEqual(payload.old_record, old_record)
        self.assertIsNone(payload.record)  # No new record for DELETE

    def test_update_payload(self):
        """Test creating an UPDATE payload."""
        record = {"id": 1, "name": "Updated Task", "completed": True}
        old_record = {"id": 1, "name": "Old Task", "completed": False}

        payload = SupabasePayload(
            type="UPDATE",
            table="tasks",
            record=record,
            old_record=old_record
        )

        self.assertEqual(payload.type, "UPDATE")
        self.assertEqual(payload.table, "tasks")
        self.assertEqual(payload.record, record)
        self.assertEqual(payload.old_record, old_record)

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing type
        with self.assertRaises(ValidationError):
            SupabasePayload(table="tasks")

        # Missing table
        with self.assertRaises(ValidationError):
            SupabasePayload(type="INSERT")

    def test_empty_string_fields(self):
        """Test behavior with empty string fields."""
        payload = SupabasePayload(
            type="",
            table=""
        )
        self.assertEqual(payload.type, "")
        self.assertEqual(payload.table, "")

    def test_complex_record_data(self):
        """Test with complex nested record data."""
        complex_record = {
            "id": 1,
            "metadata": {
                "tags": ["urgent", "important"],
                "assignee": {
                    "id": 123,
                    "name": "John Doe",
                    "email": "john@example.com"
                }
            },
            "timestamps": {
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-02T12:00:00Z"
            }
        }

        payload = SupabasePayload(
            type="INSERT",
            table="complex_tasks",
            record=complex_record
        )

        self.assertEqual(payload.record, complex_record)
        self.assertEqual(payload.record["metadata"]["tags"], ["urgent", "important"])
        self.assertEqual(payload.record["metadata"]["assignee"]["name"], "John Doe")


if __name__ == '__main__':
    unittest.main()
