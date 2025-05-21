import unittest
from unittest.mock import patch, MagicMock

# Assuming ManageLongTermMemoryTool is in src.core.tools.memory_tools
# Adjust import if necessary based on actual project structure and PYTHONPATH
from src.core.tools.memory_tools import ManageLongTermMemoryTool, ManageLongTermMemoryToolSchema

class TestManageLongTermMemoryTool(unittest.TestCase):

    def setUp(self):
        self.mock_sync_supabase_client = MagicMock()
        self.user_id = "test_user_123"
        self.agent_id = "test_agent_abc"
        self.supabase_url = "http://fake.supabase.url"
        self.supabase_key = "fake_supabase_key"

        # Patch the sync_supabase_client property to return our mock
        self.tool_patcher = patch.object(ManageLongTermMemoryTool, 'sync_supabase_client', new_callable=unittest.mock.PropertyMock)
        self.mock_sync_supabase_client_property = self.tool_patcher.start()
        self.mock_sync_supabase_client_property.return_value = self.mock_sync_supabase_client
        
        self.tool = ManageLongTermMemoryTool(
            user_id=self.user_id,
            supabase_url=self.supabase_url,
            supabase_key=self.supabase_key
        )

    def tearDown(self):
        self.tool_patcher.stop()

    def test_read_ltm_no_notes_found(self):
        # Mock Supabase response for no data
        self.mock_sync_supabase_client.table().select().eq().eq().limit().execute.return_value = MagicMock(data=[])
        
        result = self.tool._run(operation="read", agent_id=self.agent_id)
        self.assertEqual(result, f"No LTM notes found for agent '{self.agent_id}'.")
        self.mock_sync_supabase_client.table("agent_long_term_memory").select("id, notes, updated_at").eq("user_id", self.user_id).eq("agent_id", self.agent_id).limit(1).execute.assert_called_once()

    def test_read_ltm_notes_exist(self):
        expected_notes = "These are existing notes."
        self.mock_sync_supabase_client.table().select().eq().eq().limit().execute.return_value = MagicMock(data=[{"notes": expected_notes, "id": "1", "updated_at": "sometime"}])
        
        result = self.tool._run(operation="read", agent_id=self.agent_id)
        self.assertEqual(result, f"Current LTM notes for agent '{self.agent_id}':\n{expected_notes}")

    def test_overwrite_ltm_new_notes(self):
        notes_to_write = "New notes to overwrite."
        # Mock fetch existing (empty or non-existent)
        self.mock_sync_supabase_client.table().select().eq().eq().limit().execute.return_value = MagicMock(data=[])
        # Mock upsert success
        self.mock_sync_supabase_client.table().upsert().execute.return_value = MagicMock(data=[{"id": "1", "notes": notes_to_write}])

        result = self.tool._run(operation="overwrite", agent_id=self.agent_id, notes_content=notes_to_write)
        self.assertEqual(result, f"LTM notes for agent '{self.agent_id}' were successfully overwritten.")
        
        expected_upsert_data = {
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "notes": notes_to_write,
            "updated_at": "now()",
            "created_at": "now()" # Since it's treated as new
        }
        self.mock_sync_supabase_client.table("agent_long_term_memory").upsert(expected_upsert_data, on_conflict="user_id, agent_id").execute.assert_called_once()

    def test_append_ltm_no_existing_notes(self):
        notes_to_append = "Notes to append."
        self.mock_sync_supabase_client.table().select().eq().eq().limit().execute.return_value = MagicMock(data=[])
        self.mock_sync_supabase_client.table().upsert().execute.return_value = MagicMock(data=[{"id": "1"}])

        result = self.tool._run(operation="append", agent_id=self.agent_id, notes_content=notes_to_append)
        self.assertIn(f"LTM notes for agent '{self.agent_id}' were successfully appended.", result) # Exact message may vary due to timestamp
        
        # Check that notes_content in upsert starts with the "Notes started on" prefix
        # and contains the appended content.
        # Due to timestamp, we can't match exactly, so check for structure.
        args, kwargs = self.mock_sync_supabase_client.table("agent_long_term_memory").upsert.call_args
        upserted_data = args[0]
        self.assertTrue(upserted_data["notes"].startswith("-- Notes started on"))
        self.assertTrue(notes_to_append in upserted_data["notes"])

    def test_append_ltm_with_existing_notes(self):
        existing_notes = "Previous notes."
        notes_to_append = "More notes."
        self.mock_sync_supabase_client.table().select().eq().eq().limit().execute.return_value = MagicMock(data=[{"notes": existing_notes, "id": "1"}])
        self.mock_sync_supabase_client.table().upsert().execute.return_value = MagicMock(data=[{"id": "1"}])
        
        result = self.tool._run(operation="append", agent_id=self.agent_id, notes_content=notes_to_append)
        self.assertIn(f"LTM notes for agent '{self.agent_id}' were successfully appended.", result)

        args, kwargs = self.mock_sync_supabase_client.table("agent_long_term_memory").upsert.call_args
        upserted_data = args[0]
        self.assertTrue(upserted_data["notes"].startswith(existing_notes))
        self.assertTrue("-- Appended on" in upserted_data["notes"])
        self.assertTrue(notes_to_append in upserted_data["notes"])

    def test_invalid_operation(self):
        result = self.tool._run(operation="delete", agent_id=self.agent_id, notes_content="some notes")
        self.assertEqual(result, "Error: Invalid operation 'delete'. Must be 'read', 'overwrite', or 'append'.")

    def test_missing_user_id(self):
        self.tool.user_id = None
        result = self.tool._run(operation="read", agent_id=self.agent_id)
        self.assertEqual(result, "Error: User ID is not set for the tool. Cannot manage Long Term Memory.")

    def test_missing_notes_content_for_write_operations(self):
        result_overwrite = self.tool._run(operation="overwrite", agent_id=self.agent_id)
        self.assertEqual(result_overwrite, "Error: 'notes_content' is required for 'overwrite' operation.")
        
        result_append = self.tool._run(operation="append", agent_id=self.agent_id)
        self.assertEqual(result_append, "Error: 'notes_content' is required for 'append' operation.")

if __name__ == '__main__':
    unittest.main() 