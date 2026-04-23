"""Unit tests for ChatRequest model — SPEC-049 scope field."""

from pydantic import ValidationError

from chatServer.models.chat import ChatRequest


class TestChatRequestScope:
    """Test the optional scope field on ChatRequest (SPEC-049 AC-02, AC-25)."""

    def test_scope_field_absent(self):
        """Backwards compatibility: requests without scope succeed."""
        req = ChatRequest(
            agent_name="clarity",
            message="Hello",
            session_id="sess-1",
        )
        assert req.scope is None

    def test_scope_field_none(self):
        """Explicit None is accepted."""
        req = ChatRequest(
            agent_name="clarity",
            message="Hello",
            session_id="sess-1",
            scope=None,
        )
        assert req.scope is None

    def test_scope_global(self):
        req = ChatRequest(
            agent_name="clarity",
            message="Hello",
            session_id="sess-1",
            scope={"type": "global"},
        )
        assert req.scope == {"type": "global"}

    def test_scope_today(self):
        req = ChatRequest(
            agent_name="clarity",
            message="Hello",
            session_id="sess-1",
            scope={"type": "today"},
        )
        assert req.scope == {"type": "today"}

    def test_scope_file(self):
        req = ChatRequest(
            agent_name="clarity",
            message="Hello",
            session_id="sess-1",
            scope={"type": "file", "path": "notes/standup.md"},
        )
        assert req.scope["type"] == "file"
        assert req.scope["path"] == "notes/standup.md"

    def test_scope_folder(self):
        req = ChatRequest(
            agent_name="clarity",
            message="Hello",
            session_id="sess-1",
            scope={"type": "folder", "path": "projects/"},
        )
        assert req.scope["type"] == "folder"
        assert req.scope["path"] == "projects/"

    def test_scope_workflow(self):
        req = ChatRequest(
            agent_name="clarity",
            message="Hello",
            session_id="sess-1",
            scope={"type": "workflow", "path": "_workflows/morning.flow.md"},
        )
        assert req.scope["type"] == "workflow"
        assert req.scope["path"] == "_workflows/morning.flow.md"

    def test_scope_unknown_type_accepted(self):
        """Unknown scope types are accepted (dict is unvalidated)."""
        req = ChatRequest(
            agent_name="clarity",
            message="Hello",
            session_id="sess-1",
            scope={"type": "unknown_future_type"},
        )
        assert req.scope["type"] == "unknown_future_type"

    def test_scope_extra_fields_accepted(self):
        """Extra keys in the scope dict do not cause validation errors."""
        req = ChatRequest(
            agent_name="clarity",
            message="Hello",
            session_id="sess-1",
            scope={"type": "file", "path": "a.md", "extra": True},
        )
        assert req.scope["extra"] is True

    def test_required_fields_still_enforced(self):
        """Adding scope does not break required field validation."""
        with __import__("pytest").raises(ValidationError):
            ChatRequest(
                agent_name="clarity",
                session_id="sess-1",
                scope={"type": "today"},
                # message is missing
            )
