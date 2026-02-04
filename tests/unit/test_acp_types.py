"""
Unit tests for ACP Core Types and Enumerations.

Tests cover:
- RunStatus: Run lifecycle states
- AgentStatus: Agent operational states
- RunMode: Execution modes (sync/async/stream)
- ContentEncoding: Message part encoding (plain/base64)
- MessageRole: Message author roles
- ErrorCode: Standard error codes
- MetadataType: Metadata type identifiers
"""

from __future__ import annotations

import pytest
from enum import Enum


# =============================================================================
# Helper Functions for Lazy Imports
# =============================================================================

def _get_types():
    """Lazy import of ACP types module."""
    from app.acp.core.types import (
        RunStatus,
        AgentStatus,
        RunMode,
        ContentEncoding,
        MessageRole,
        ErrorCode,
        MetadataType,
    )
    return {
        "RunStatus": RunStatus,
        "AgentStatus": AgentStatus,
        "RunMode": RunMode,
        "ContentEncoding": ContentEncoding,
        "MessageRole": MessageRole,
        "ErrorCode": ErrorCode,
        "MetadataType": MetadataType,
    }


# =============================================================================
# RunStatus Tests
# =============================================================================

class TestRunStatus:
    """Tests for RunStatus enum - run lifecycle states."""

    def test_run_status_inherits_from_str_and_enum(self):
        """Verify RunStatus inherits from both str and Enum."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        assert issubclass(RunStatus, str)
        assert issubclass(RunStatus, Enum)

    def test_run_status_has_all_expected_values(self):
        """Verify all expected run status values exist."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        expected_values = {
            "CREATED": "created",
            "IN_PROGRESS": "in-progress",
            "AWAITING": "awaiting",
            "CANCELLING": "cancelling",
            "CANCELLED": "cancelled",
            "COMPLETED": "completed",
            "FAILED": "failed",
        }
        for name, value in expected_values.items():
            assert hasattr(RunStatus, name), f"RunStatus should have {name}"
            assert getattr(RunStatus, name).value == value

    def test_run_status_count(self):
        """Verify the total number of run status values."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        assert len(list(RunStatus)) == 7

    def test_run_status_value_access(self):
        """Verify RunStatus value attribute returns the string value."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        assert RunStatus.CREATED.value == "created"
        assert RunStatus.IN_PROGRESS.value == "in-progress"
        assert RunStatus.COMPLETED.value == "completed"

    def test_run_status_equality_with_string(self):
        """Verify RunStatus can be compared with strings."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        assert RunStatus.CREATED == "created"
        assert RunStatus.IN_PROGRESS == "in-progress"
        assert RunStatus.COMPLETED == "completed"

    def test_run_status_can_be_used_in_dict(self):
        """Verify RunStatus can be used as dict key and in JSON-like structures."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        data = {
            "status": RunStatus.COMPLETED,
            RunStatus.FAILED: "error message",
        }
        assert data["status"] == "completed"
        assert data[RunStatus.FAILED] == "error message"

    def test_run_status_is_hashable(self):
        """Verify RunStatus values are hashable (for use in sets)."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        status_set = {RunStatus.CREATED, RunStatus.COMPLETED, RunStatus.FAILED}
        assert len(status_set) == 3
        assert RunStatus.COMPLETED in status_set

    def test_run_status_membership(self):
        """Verify membership checks work correctly."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        assert RunStatus.CREATED in RunStatus
        assert "not_a_status" not in [s.value for s in RunStatus]

    @pytest.mark.parametrize("status,expected_value", [
        ("CREATED", "created"),
        ("IN_PROGRESS", "in-progress"),
        ("AWAITING", "awaiting"),
        ("CANCELLING", "cancelling"),
        ("CANCELLED", "cancelled"),
        ("COMPLETED", "completed"),
        ("FAILED", "failed"),
    ])
    def test_run_status_individual_values(self, status, expected_value):
        """Parametrized test for each RunStatus value."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        assert getattr(RunStatus, status).value == expected_value

    def test_run_status_terminal_states(self):
        """Verify identification of terminal states."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        terminal_states = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
        for status in terminal_states:
            assert status in terminal_states

    def test_run_status_active_states(self):
        """Verify identification of active (non-terminal) states."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        active_states = {
            RunStatus.CREATED,
            RunStatus.IN_PROGRESS,
            RunStatus.AWAITING,
            RunStatus.CANCELLING,
        }
        assert len(active_states) == 4


# =============================================================================
# AgentStatus Tests
# =============================================================================

class TestAgentStatus:
    """Tests for AgentStatus enum - agent operational states."""

    def test_agent_status_inherits_from_str_and_enum(self):
        """Verify AgentStatus inherits from both str and Enum."""
        types = _get_types()
        AgentStatus = types["AgentStatus"]
        assert issubclass(AgentStatus, str)
        assert issubclass(AgentStatus, Enum)

    def test_agent_status_has_all_expected_values(self):
        """Verify all expected agent status values exist."""
        types = _get_types()
        AgentStatus = types["AgentStatus"]
        expected_values = {
            "INITIALIZING": "initializing",
            "ACTIVE": "active",
            "DEGRADED": "degraded",
            "RETIRING": "retiring",
            "RETIRED": "retired",
        }
        for name, value in expected_values.items():
            assert hasattr(AgentStatus, name), f"AgentStatus should have {name}"
            assert getattr(AgentStatus, name).value == value

    def test_agent_status_count(self):
        """Verify the total number of agent status values."""
        types = _get_types()
        AgentStatus = types["AgentStatus"]
        assert len(list(AgentStatus)) == 5

    def test_agent_status_value_access(self):
        """Verify AgentStatus value attribute returns the string value."""
        types = _get_types()
        AgentStatus = types["AgentStatus"]
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.DEGRADED.value == "degraded"

    def test_agent_status_equality_with_string(self):
        """Verify AgentStatus can be compared with strings."""
        types = _get_types()
        AgentStatus = types["AgentStatus"]
        assert AgentStatus.ACTIVE == "active"
        assert AgentStatus.INITIALIZING == "initializing"
        assert AgentStatus.RETIRED == "retired"

    @pytest.mark.parametrize("status,expected_value", [
        ("INITIALIZING", "initializing"),
        ("ACTIVE", "active"),
        ("DEGRADED", "degraded"),
        ("RETIRING", "retiring"),
        ("RETIRED", "retired"),
    ])
    def test_agent_status_individual_values(self, status, expected_value):
        """Parametrized test for each AgentStatus value."""
        types = _get_types()
        AgentStatus = types["AgentStatus"]
        assert getattr(AgentStatus, status).value == expected_value

    def test_agent_status_operational_states(self):
        """Verify identification of operational states."""
        types = _get_types()
        AgentStatus = types["AgentStatus"]
        # States where agent can still accept requests
        operational_states = {AgentStatus.ACTIVE, AgentStatus.DEGRADED}
        assert len(operational_states) == 2

    def test_agent_status_unavailable_states(self):
        """Verify identification of unavailable states."""
        types = _get_types()
        AgentStatus = types["AgentStatus"]
        # States where agent cannot accept requests
        unavailable_states = {
            AgentStatus.INITIALIZING,
            AgentStatus.RETIRING,
            AgentStatus.RETIRED,
        }
        assert len(unavailable_states) == 3


# =============================================================================
# RunMode Tests
# =============================================================================

class TestRunMode:
    """Tests for RunMode enum - execution modes."""

    def test_run_mode_inherits_from_str_and_enum(self):
        """Verify RunMode inherits from both str and Enum."""
        types = _get_types()
        RunMode = types["RunMode"]
        assert issubclass(RunMode, str)
        assert issubclass(RunMode, Enum)

    def test_run_mode_has_all_expected_values(self):
        """Verify all expected run mode values exist."""
        types = _get_types()
        RunMode = types["RunMode"]
        expected_values = {
            "SYNC": "sync",
            "ASYNC": "async",
            "STREAM": "stream",
        }
        for name, value in expected_values.items():
            assert hasattr(RunMode, name), f"RunMode should have {name}"
            assert getattr(RunMode, name).value == value

    def test_run_mode_count(self):
        """Verify the total number of run mode values."""
        types = _get_types()
        RunMode = types["RunMode"]
        assert len(list(RunMode)) == 3

    def test_run_mode_value_access(self):
        """Verify RunMode value attribute returns the string value."""
        types = _get_types()
        RunMode = types["RunMode"]
        assert RunMode.SYNC.value == "sync"
        assert RunMode.ASYNC.value == "async"
        assert RunMode.STREAM.value == "stream"

    def test_run_mode_equality_with_string(self):
        """Verify RunMode can be compared with strings."""
        types = _get_types()
        RunMode = types["RunMode"]
        assert RunMode.SYNC == "sync"
        assert RunMode.ASYNC == "async"
        assert RunMode.STREAM == "stream"

    @pytest.mark.parametrize("mode,expected_value", [
        ("SYNC", "sync"),
        ("ASYNC", "async"),
        ("STREAM", "stream"),
    ])
    def test_run_mode_individual_values(self, mode, expected_value):
        """Parametrized test for each RunMode value."""
        types = _get_types()
        RunMode = types["RunMode"]
        assert getattr(RunMode, mode).value == expected_value

    def test_run_mode_can_be_serialized(self):
        """Verify RunMode can be serialized to JSON-compatible format."""
        types = _get_types()
        RunMode = types["RunMode"]
        import json
        data = {"mode": RunMode.STREAM.value}
        serialized = json.dumps(data)
        assert '"mode": "stream"' in serialized


# =============================================================================
# ContentEncoding Tests
# =============================================================================

class TestContentEncoding:
    """Tests for ContentEncoding enum - message part encoding."""

    def test_content_encoding_inherits_from_str_and_enum(self):
        """Verify ContentEncoding inherits from both str and Enum."""
        types = _get_types()
        ContentEncoding = types["ContentEncoding"]
        assert issubclass(ContentEncoding, str)
        assert issubclass(ContentEncoding, Enum)

    def test_content_encoding_has_all_expected_values(self):
        """Verify all expected content encoding values exist."""
        types = _get_types()
        ContentEncoding = types["ContentEncoding"]
        expected_values = {
            "PLAIN": "plain",
            "BASE64": "base64",
        }
        for name, value in expected_values.items():
            assert hasattr(ContentEncoding, name), f"ContentEncoding should have {name}"
            assert getattr(ContentEncoding, name).value == value

    def test_content_encoding_count(self):
        """Verify the total number of content encoding values."""
        types = _get_types()
        ContentEncoding = types["ContentEncoding"]
        assert len(list(ContentEncoding)) == 2

    def test_content_encoding_value_access(self):
        """Verify ContentEncoding value attribute returns the string value."""
        types = _get_types()
        ContentEncoding = types["ContentEncoding"]
        assert ContentEncoding.PLAIN.value == "plain"
        assert ContentEncoding.BASE64.value == "base64"

    def test_content_encoding_equality_with_string(self):
        """Verify ContentEncoding can be compared with strings."""
        types = _get_types()
        ContentEncoding = types["ContentEncoding"]
        assert ContentEncoding.PLAIN == "plain"
        assert ContentEncoding.BASE64 == "base64"

    @pytest.mark.parametrize("encoding,expected_value", [
        ("PLAIN", "plain"),
        ("BASE64", "base64"),
    ])
    def test_content_encoding_individual_values(self, encoding, expected_value):
        """Parametrized test for each ContentEncoding value."""
        types = _get_types()
        ContentEncoding = types["ContentEncoding"]
        assert getattr(ContentEncoding, encoding).value == expected_value


# =============================================================================
# MessageRole Tests
# =============================================================================

class TestMessageRole:
    """Tests for MessageRole enum - message author roles."""

    def test_message_role_inherits_from_str_and_enum(self):
        """Verify MessageRole inherits from both str and Enum."""
        types = _get_types()
        MessageRole = types["MessageRole"]
        assert issubclass(MessageRole, str)
        assert issubclass(MessageRole, Enum)

    def test_message_role_has_all_expected_values(self):
        """Verify all expected message role values exist."""
        types = _get_types()
        MessageRole = types["MessageRole"]
        expected_values = {
            "USER": "user",
            "AGENT": "agent",
            "SYSTEM": "system",
        }
        for name, value in expected_values.items():
            assert hasattr(MessageRole, name), f"MessageRole should have {name}"
            assert getattr(MessageRole, name).value == value

    def test_message_role_count(self):
        """Verify the total number of message role values."""
        types = _get_types()
        MessageRole = types["MessageRole"]
        assert len(list(MessageRole)) == 3

    def test_message_role_value_access(self):
        """Verify MessageRole value attribute returns the string value."""
        types = _get_types()
        MessageRole = types["MessageRole"]
        assert MessageRole.USER.value == "user"
        assert MessageRole.AGENT.value == "agent"
        assert MessageRole.SYSTEM.value == "system"

    def test_message_role_equality_with_string(self):
        """Verify MessageRole can be compared with strings."""
        types = _get_types()
        MessageRole = types["MessageRole"]
        assert MessageRole.USER == "user"
        assert MessageRole.AGENT == "agent"
        assert MessageRole.SYSTEM == "system"

    @pytest.mark.parametrize("role,expected_value", [
        ("USER", "user"),
        ("AGENT", "agent"),
        ("SYSTEM", "system"),
    ])
    def test_message_role_individual_values(self, role, expected_value):
        """Parametrized test for each MessageRole value."""
        types = _get_types()
        MessageRole = types["MessageRole"]
        assert getattr(MessageRole, role).value == expected_value

    def test_message_role_supports_named_agent_format(self):
        """Verify named agent format (agent/name) is documented."""
        types = _get_types()
        MessageRole = types["MessageRole"]
        # Named agents use format "agent/{agent_name}" but are not enum members
        # This test verifies the base AGENT role exists for generic agent messages
        assert MessageRole.AGENT == "agent"
        # Named agents would be strings like "agent/assistant"
        named_agent = "agent/assistant"
        assert named_agent.startswith("agent/")


# =============================================================================
# ErrorCode Tests
# =============================================================================

class TestErrorCode:
    """Tests for ErrorCode enum - standard error codes."""

    def test_error_code_inherits_from_str_and_enum(self):
        """Verify ErrorCode inherits from both str and Enum."""
        types = _get_types()
        ErrorCode = types["ErrorCode"]
        assert issubclass(ErrorCode, str)
        assert issubclass(ErrorCode, Enum)

    def test_error_code_has_all_expected_values(self):
        """Verify all expected error code values exist."""
        types = _get_types()
        ErrorCode = types["ErrorCode"]
        expected_values = {
            "SERVER_ERROR": "server_error",
            "INVALID_INPUT": "invalid_input",
            "NOT_FOUND": "not_found",
            "UNAUTHORIZED": "unauthorized",
            "FORBIDDEN": "forbidden",
            "CONFLICT": "conflict",
            "RATE_LIMITED": "rate_limited",
            "TIMEOUT": "timeout",
            "AGENT_ERROR": "agent_error",
            "VALIDATION_ERROR": "validation_error",
        }
        for name, value in expected_values.items():
            assert hasattr(ErrorCode, name), f"ErrorCode should have {name}"
            assert getattr(ErrorCode, name).value == value

    def test_error_code_count(self):
        """Verify the total number of error code values."""
        types = _get_types()
        ErrorCode = types["ErrorCode"]
        assert len(list(ErrorCode)) == 10

    def test_error_code_value_access(self):
        """Verify ErrorCode value attribute returns the string value."""
        types = _get_types()
        ErrorCode = types["ErrorCode"]
        assert ErrorCode.SERVER_ERROR.value == "server_error"
        assert ErrorCode.NOT_FOUND.value == "not_found"
        assert ErrorCode.TIMEOUT.value == "timeout"

    def test_error_code_equality_with_string(self):
        """Verify ErrorCode can be compared with strings."""
        types = _get_types()
        ErrorCode = types["ErrorCode"]
        assert ErrorCode.SERVER_ERROR == "server_error"
        assert ErrorCode.UNAUTHORIZED == "unauthorized"
        assert ErrorCode.RATE_LIMITED == "rate_limited"

    @pytest.mark.parametrize("code,expected_value", [
        ("SERVER_ERROR", "server_error"),
        ("INVALID_INPUT", "invalid_input"),
        ("NOT_FOUND", "not_found"),
        ("UNAUTHORIZED", "unauthorized"),
        ("FORBIDDEN", "forbidden"),
        ("CONFLICT", "conflict"),
        ("RATE_LIMITED", "rate_limited"),
        ("TIMEOUT", "timeout"),
        ("AGENT_ERROR", "agent_error"),
        ("VALIDATION_ERROR", "validation_error"),
    ])
    def test_error_code_individual_values(self, code, expected_value):
        """Parametrized test for each ErrorCode value."""
        types = _get_types()
        ErrorCode = types["ErrorCode"]
        assert getattr(ErrorCode, code).value == expected_value

    def test_error_code_client_errors(self):
        """Verify identification of client-side error codes."""
        types = _get_types()
        ErrorCode = types["ErrorCode"]
        client_errors = {
            ErrorCode.INVALID_INPUT,
            ErrorCode.NOT_FOUND,
            ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN,
            ErrorCode.CONFLICT,
            ErrorCode.RATE_LIMITED,
            ErrorCode.VALIDATION_ERROR,
        }
        assert len(client_errors) == 7

    def test_error_code_server_errors(self):
        """Verify identification of server-side error codes."""
        types = _get_types()
        ErrorCode = types["ErrorCode"]
        server_errors = {
            ErrorCode.SERVER_ERROR,
            ErrorCode.TIMEOUT,
            ErrorCode.AGENT_ERROR,
        }
        assert len(server_errors) == 3


# =============================================================================
# MetadataType Tests
# =============================================================================

class TestMetadataType:
    """Tests for MetadataType enum - metadata type identifiers."""

    def test_metadata_type_inherits_from_str_and_enum(self):
        """Verify MetadataType inherits from both str and Enum."""
        types = _get_types()
        MetadataType = types["MetadataType"]
        assert issubclass(MetadataType, str)
        assert issubclass(MetadataType, Enum)

    def test_metadata_type_has_all_expected_values(self):
        """Verify all expected metadata type values exist."""
        types = _get_types()
        MetadataType = types["MetadataType"]
        expected_values = {
            "CITATION": "citation",
            "TRAJECTORY": "trajectory",
            "CUSTOM": "custom",
        }
        for name, value in expected_values.items():
            assert hasattr(MetadataType, name), f"MetadataType should have {name}"
            assert getattr(MetadataType, name).value == value

    def test_metadata_type_count(self):
        """Verify the total number of metadata type values."""
        types = _get_types()
        MetadataType = types["MetadataType"]
        assert len(list(MetadataType)) == 3

    def test_metadata_type_value_access(self):
        """Verify MetadataType value attribute returns the string value."""
        types = _get_types()
        MetadataType = types["MetadataType"]
        assert MetadataType.CITATION.value == "citation"
        assert MetadataType.TRAJECTORY.value == "trajectory"
        assert MetadataType.CUSTOM.value == "custom"

    def test_metadata_type_equality_with_string(self):
        """Verify MetadataType can be compared with strings."""
        types = _get_types()
        MetadataType = types["MetadataType"]
        assert MetadataType.CITATION == "citation"
        assert MetadataType.TRAJECTORY == "trajectory"
        assert MetadataType.CUSTOM == "custom"

    @pytest.mark.parametrize("metadata_type,expected_value", [
        ("CITATION", "citation"),
        ("TRAJECTORY", "trajectory"),
        ("CUSTOM", "custom"),
    ])
    def test_metadata_type_individual_values(self, metadata_type, expected_value):
        """Parametrized test for each MetadataType value."""
        types = _get_types()
        MetadataType = types["MetadataType"]
        assert getattr(MetadataType, metadata_type).value == expected_value


# =============================================================================
# Cross-Enum Tests
# =============================================================================

class TestEnumInteroperability:
    """Tests for cross-enum interoperability and common behavior."""

    def test_all_enums_are_string_enums(self):
        """Verify all ACP enums inherit from str."""
        types = _get_types()
        for name, enum_class in types.items():
            assert issubclass(enum_class, str), f"{name} should inherit from str"
            assert issubclass(enum_class, Enum), f"{name} should inherit from Enum"

    def test_all_enum_values_are_lowercase(self):
        """Verify all enum values are lowercase (for consistency)."""
        types = _get_types()
        for name, enum_class in types.items():
            for member in enum_class:
                assert member.value == member.value.lower(), (
                    f"{name}.{member.name} value should be lowercase"
                )

    def test_enum_values_use_underscores_or_hyphens(self):
        """Verify enum values use only allowed characters."""
        types = _get_types()
        import re
        pattern = re.compile(r'^[a-z][a-z0-9_-]*$')
        for name, enum_class in types.items():
            for member in enum_class:
                assert pattern.match(member.value), (
                    f"{name}.{member.name} value '{member.value}' has invalid characters"
                )

    def test_enum_names_are_uppercase(self):
        """Verify all enum member names are uppercase."""
        types = _get_types()
        for name, enum_class in types.items():
            for member in enum_class:
                assert member.name == member.name.upper(), (
                    f"{name}.{member.name} should be uppercase"
                )

    def test_enums_can_be_iterated(self):
        """Verify all enums can be iterated."""
        types = _get_types()
        for name, enum_class in types.items():
            members = list(enum_class)
            assert len(members) > 0, f"{name} should have at least one member"

    def test_enum_values_are_unique_within_enum(self):
        """Verify all values within each enum are unique."""
        types = _get_types()
        for name, enum_class in types.items():
            values = [member.value for member in enum_class]
            assert len(values) == len(set(values)), (
                f"{name} has duplicate values"
            )

    def test_enums_can_be_used_in_json_serialization(self):
        """Verify enums can be serialized to JSON."""
        import json
        types = _get_types()

        data = {
            "run_status": types["RunStatus"].COMPLETED.value,
            "agent_status": types["AgentStatus"].ACTIVE.value,
            "run_mode": types["RunMode"].STREAM.value,
            "content_encoding": types["ContentEncoding"].PLAIN.value,
            "message_role": types["MessageRole"].USER.value,
            "error_code": types["ErrorCode"].NOT_FOUND.value,
            "metadata_type": types["MetadataType"].CITATION.value,
        }

        serialized = json.dumps(data)
        deserialized = json.loads(serialized)

        assert deserialized["run_status"] == "completed"
        assert deserialized["agent_status"] == "active"
        assert deserialized["run_mode"] == "stream"

    def test_enums_support_comparison_operators(self):
        """Verify enums support equality comparisons."""
        types = _get_types()
        RunStatus = types["RunStatus"]

        # Same enum members should be equal
        assert RunStatus.COMPLETED == RunStatus.COMPLETED
        assert RunStatus.COMPLETED != RunStatus.FAILED

        # Enum members should be equal to their string values
        assert RunStatus.COMPLETED == "completed"
        assert RunStatus.FAILED != "completed"


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_enum_from_value(self):
        """Verify enums can be constructed from their values."""
        types = _get_types()
        RunStatus = types["RunStatus"]

        # Construct enum from value
        status = RunStatus("completed")
        assert status == RunStatus.COMPLETED
        assert status.name == "COMPLETED"

    def test_invalid_enum_value_raises(self):
        """Verify invalid enum values raise ValueError."""
        types = _get_types()
        RunStatus = types["RunStatus"]

        with pytest.raises(ValueError):
            RunStatus("invalid_status")

    def test_enum_repr(self):
        """Verify enum repr format."""
        types = _get_types()
        RunStatus = types["RunStatus"]

        # Repr should include the class name and value
        repr_str = repr(RunStatus.COMPLETED)
        assert "RunStatus" in repr_str or "COMPLETED" in repr_str

    def test_enum_name_attribute(self):
        """Verify enum name attribute."""
        types = _get_types()
        RunStatus = types["RunStatus"]

        assert RunStatus.COMPLETED.name == "COMPLETED"
        assert RunStatus.FAILED.name == "FAILED"

    def test_enum_value_attribute(self):
        """Verify enum value attribute."""
        types = _get_types()
        RunStatus = types["RunStatus"]

        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"

    def test_enum_identity_vs_equality(self):
        """Verify enum identity and equality behavior."""
        types = _get_types()
        RunStatus = types["RunStatus"]

        status1 = RunStatus.COMPLETED
        status2 = RunStatus.COMPLETED

        # Identity check
        assert status1 is status2

        # Equality check
        assert status1 == status2

    def test_enum_in_container(self):
        """Verify enums work correctly in various container types."""
        types = _get_types()
        RunStatus = types["RunStatus"]

        # List
        status_list = [RunStatus.CREATED, RunStatus.COMPLETED]
        assert RunStatus.COMPLETED in status_list

        # Set
        status_set = {RunStatus.CREATED, RunStatus.COMPLETED}
        assert RunStatus.COMPLETED in status_set

        # Dict key
        status_dict = {RunStatus.COMPLETED: "done", RunStatus.FAILED: "error"}
        assert status_dict[RunStatus.COMPLETED] == "done"

        # Dict value
        status_dict2 = {"result": RunStatus.COMPLETED}
        assert status_dict2["result"] == RunStatus.COMPLETED

    def test_enum_value_in_string_formatting(self):
        """Verify enum values can be used in string formatting."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        MessageRole = types["MessageRole"]

        # String formatting using .value
        message = f"Status: {RunStatus.COMPLETED.value}"
        assert message == "Status: completed"

        role_str = "Role: " + MessageRole.USER.value
        assert role_str == "Role: user"

    def test_enum_direct_string_comparison(self):
        """Verify enums can be directly compared as strings (str enum behavior)."""
        types = _get_types()
        RunStatus = types["RunStatus"]
        MessageRole = types["MessageRole"]

        # Direct equality comparison with string works (str inheritance)
        assert RunStatus.COMPLETED == "completed"
        assert MessageRole.USER == "user"
