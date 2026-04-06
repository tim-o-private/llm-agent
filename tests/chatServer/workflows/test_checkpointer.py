"""Tests for WorkflowCheckpointer — unit tests only (no real Postgres)."""

from unittest.mock import patch

import pytest

from chatServer.workflows.checkpointer import WorkflowCheckpointer, _build_database_url


class TestBuildDatabaseUrl:
    def test_default_url(self):
        with patch.dict("os.environ", {}, clear=True):
            url = _build_database_url()
            assert url == "postgresql://postgres:@localhost:5432/postgres"

    def test_custom_url(self):
        env = {
            "SUPABASE_DB_HOST": "db.example.com",
            "SUPABASE_DB_PORT": "6543",
            "SUPABASE_DB_NAME": "mydb",
            "SUPABASE_DB_USER": "admin",
            "SUPABASE_DB_PASSWORD": "secret",
        }
        with patch.dict("os.environ", env, clear=True):
            url = _build_database_url()
            assert url == "postgresql://admin:secret@db.example.com:6543/mydb"


class TestCheckpointerLifecycle:
    def test_not_ready_before_setup(self):
        cp = WorkflowCheckpointer("postgresql://localhost/test")
        assert cp.is_ready is False

    def test_saver_raises_before_setup(self):
        cp = WorkflowCheckpointer("postgresql://localhost/test")
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = cp.saver

    @pytest.mark.asyncio
    async def test_shutdown_noop_before_setup(self):
        cp = WorkflowCheckpointer("postgresql://localhost/test")
        # Should not raise
        await cp.shutdown()
        assert cp.is_ready is False
