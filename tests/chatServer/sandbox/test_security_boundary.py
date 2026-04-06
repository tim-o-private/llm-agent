"""Tests for SecurityBoundary — path classification and write validation."""

from chatServer.sandbox.security_boundary import (
    ModificationPolicy,
    SecurityBoundary,
    load_policy,
)


class TestClassifyPath:
    def test_system_path_is_immutable(self):
        boundary = SecurityBoundary()
        assert boundary.classify_path("/system/security/tool_allowlist.yaml") == "immutable"

    def test_system_root_is_immutable(self):
        boundary = SecurityBoundary()
        assert boundary.classify_path("/system/agents/clarity/soul.md") == "immutable"

    def test_user_agent_is_mutable(self):
        boundary = SecurityBoundary()
        assert boundary.classify_path("/user/agent/style_overrides.md") == "mutable"

    def test_user_preferences_is_mutable(self):
        boundary = SecurityBoundary()
        assert boundary.classify_path("/user/preferences/scheduling.yaml") == "mutable"

    def test_user_workflows_is_mutable(self):
        boundary = SecurityBoundary()
        assert boundary.classify_path("/user/workflows/custom_triage.md") == "mutable"

    def test_user_memory_is_mutable(self):
        boundary = SecurityBoundary()
        assert boundary.classify_path("/user/memory/observations.md") == "mutable"

    def test_user_schedules_is_mutable(self):
        boundary = SecurityBoundary()
        assert boundary.classify_path("/user/schedules/weekly.yaml") == "mutable"

    def test_unknown_path(self):
        boundary = SecurityBoundary()
        assert boundary.classify_path("/tmp/scratch.txt") == "unknown"

    def test_user_root_file_is_unknown(self):
        boundary = SecurityBoundary()
        # /user/README.md doesn't match /user/agent/** etc.
        assert boundary.classify_path("/user/README.md") == "unknown"

    def test_tools_path_is_unknown(self):
        boundary = SecurityBoundary()
        assert boundary.classify_path("/tools/git") == "unknown"


class TestValidateWrite:
    def test_allows_mutable_writes(self):
        boundary = SecurityBoundary()
        assert boundary.validate_write("/user/agent/greeting.md") is True

    def test_rejects_immutable_writes(self):
        boundary = SecurityBoundary()
        assert boundary.validate_write("/system/security/tool_allowlist.yaml") is False

    def test_rejects_unknown_writes(self):
        boundary = SecurityBoundary()
        assert boundary.validate_write("/tmp/scratch.txt") is False

    def test_rejects_system_root_writes(self):
        boundary = SecurityBoundary()
        assert boundary.validate_write("/system/anything") is False


class TestRequiresElevatedReview:
    def test_workflow_requires_review(self):
        boundary = SecurityBoundary()
        assert boundary.requires_elevated_review("/user/workflows/custom.md") is True

    def test_preferences_no_review(self):
        boundary = SecurityBoundary()
        assert boundary.requires_elevated_review("/user/preferences/style.yaml") is False

    def test_agent_no_review(self):
        boundary = SecurityBoundary()
        assert boundary.requires_elevated_review("/user/agent/greeting.md") is False


class TestLoadPolicy:
    def test_default_policy(self):
        policy = load_policy(None)
        assert "/system/**" in policy.immutable_paths
        assert len(policy.mutable_paths) == 5

    def test_custom_policy_from_dict(self):
        data = {
            "immutable_paths": ["/locked/**"],
            "mutable_paths": ["/open/**"],
            "elevated_review": [],
        }
        policy = load_policy(data)
        assert policy.immutable_paths == ["/locked/**"]
        assert policy.mutable_paths == ["/open/**"]

    def test_custom_policy_classification(self):
        policy = ModificationPolicy(
            immutable_paths=["/locked/**"],
            mutable_paths=["/open/**"],
        )
        boundary = SecurityBoundary(policy)
        assert boundary.classify_path("/locked/secret.yaml") == "immutable"
        assert boundary.classify_path("/open/file.md") == "mutable"
        assert boundary.classify_path("/system/anything") == "unknown"
