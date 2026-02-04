"""
Unit tests for RunStateMachine state transitions.

Tests cover:
- State machine initialization
- Valid state transitions according to ACP specification
- Invalid state transitions and error handling
- Terminal state behavior
- State transition history tracking
- Callback registration and execution
- Duration and timing calculations
- RunLifecycleManager high-level operations
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Helper Functions for Lazy Imports
# =============================================================================

def _get_types():
    """Lazy import of ACP types module."""
    from app.acp.core.types import RunStatus
    return {"RunStatus": RunStatus}


def _get_lifecycle():
    """Lazy import of lifecycle module."""
    from app.acp.protocol.lifecycle import (
        RunStateMachine,
        StateTransition,
        InvalidTransitionError,
        RunLifecycleManager,
    )
    return {
        "RunStateMachine": RunStateMachine,
        "StateTransition": StateTransition,
        "InvalidTransitionError": InvalidTransitionError,
        "RunLifecycleManager": RunLifecycleManager,
    }


# =============================================================================
# RunStateMachine Initialization Tests
# =============================================================================

class TestRunStateMachineInitialization:
    """Tests for RunStateMachine initialization and default state."""

    def test_default_initial_state_is_created(self):
        """Verify state machine starts in CREATED state by default."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        assert machine.current_state == types["RunStatus"].CREATED

    def test_custom_initial_state(self):
        """Verify state machine can start with a custom initial state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].IN_PROGRESS
        )

        assert machine.current_state == types["RunStatus"].IN_PROGRESS

    def test_initial_history_is_empty(self):
        """Verify state machine starts with empty history."""
        lifecycle = _get_lifecycle()

        machine = lifecycle["RunStateMachine"]()

        assert machine.history == []
        assert len(machine.history) == 0

    def test_initial_state_is_not_terminal(self):
        """Verify initial CREATED state is not terminal."""
        lifecycle = _get_lifecycle()

        machine = lifecycle["RunStateMachine"]()

        assert machine.is_terminal is False

    @pytest.mark.parametrize("terminal_state", ["COMPLETED", "FAILED", "CANCELLED"])
    def test_terminal_states_are_terminal(self, terminal_state):
        """Verify terminal states are recognized as terminal."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        status = getattr(types["RunStatus"], terminal_state)
        machine = lifecycle["RunStateMachine"](initial_state=status)

        assert machine.is_terminal is True


# =============================================================================
# Valid State Transition Tests
# =============================================================================

class TestValidStateTransitions:
    """Tests for valid state transitions according to ACP specification."""

    @pytest.mark.asyncio
    async def test_created_to_in_progress(self):
        """Verify CREATED -> IN_PROGRESS transition."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        assert machine.current_state == types["RunStatus"].CREATED

        transition = await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        assert machine.current_state == types["RunStatus"].IN_PROGRESS
        assert transition.from_state == types["RunStatus"].CREATED
        assert transition.to_state == types["RunStatus"].IN_PROGRESS

    @pytest.mark.asyncio
    async def test_created_to_cancelled(self):
        """Verify CREATED -> CANCELLED transition (cancel before start)."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        transition = await machine.transition_to(types["RunStatus"].CANCELLED)

        assert machine.current_state == types["RunStatus"].CANCELLED
        assert transition.from_state == types["RunStatus"].CREATED

    @pytest.mark.asyncio
    async def test_in_progress_to_completed(self):
        """Verify IN_PROGRESS -> COMPLETED transition."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].IN_PROGRESS
        )

        transition = await machine.transition_to(types["RunStatus"].COMPLETED)

        assert machine.current_state == types["RunStatus"].COMPLETED
        assert machine.is_terminal is True

    @pytest.mark.asyncio
    async def test_in_progress_to_failed(self):
        """Verify IN_PROGRESS -> FAILED transition."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].IN_PROGRESS
        )

        transition = await machine.transition_to(types["RunStatus"].FAILED)

        assert machine.current_state == types["RunStatus"].FAILED
        assert machine.is_terminal is True

    @pytest.mark.asyncio
    async def test_in_progress_to_awaiting(self):
        """Verify IN_PROGRESS -> AWAITING transition."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].IN_PROGRESS
        )

        transition = await machine.transition_to(types["RunStatus"].AWAITING)

        assert machine.current_state == types["RunStatus"].AWAITING
        assert machine.is_terminal is False

    @pytest.mark.asyncio
    async def test_in_progress_to_cancelling(self):
        """Verify IN_PROGRESS -> CANCELLING transition."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].IN_PROGRESS
        )

        transition = await machine.transition_to(types["RunStatus"].CANCELLING)

        assert machine.current_state == types["RunStatus"].CANCELLING

    @pytest.mark.asyncio
    async def test_awaiting_to_in_progress(self):
        """Verify AWAITING -> IN_PROGRESS transition (resume)."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].AWAITING
        )

        transition = await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        assert machine.current_state == types["RunStatus"].IN_PROGRESS

    @pytest.mark.asyncio
    async def test_awaiting_to_cancelling(self):
        """Verify AWAITING -> CANCELLING transition."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].AWAITING
        )

        transition = await machine.transition_to(types["RunStatus"].CANCELLING)

        assert machine.current_state == types["RunStatus"].CANCELLING

    @pytest.mark.asyncio
    async def test_awaiting_to_failed(self):
        """Verify AWAITING -> FAILED transition (timeout)."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].AWAITING
        )

        transition = await machine.transition_to(types["RunStatus"].FAILED)

        assert machine.current_state == types["RunStatus"].FAILED

    @pytest.mark.asyncio
    async def test_cancelling_to_cancelled(self):
        """Verify CANCELLING -> CANCELLED transition."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].CANCELLING
        )

        transition = await machine.transition_to(types["RunStatus"].CANCELLED)

        assert machine.current_state == types["RunStatus"].CANCELLED
        assert machine.is_terminal is True


# =============================================================================
# Invalid State Transition Tests
# =============================================================================

class TestInvalidStateTransitions:
    """Tests for invalid state transitions that should raise errors."""

    @pytest.mark.asyncio
    async def test_created_to_completed_invalid(self):
        """Verify CREATED -> COMPLETED is invalid (must go through IN_PROGRESS)."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        with pytest.raises(lifecycle["InvalidTransitionError"]) as exc_info:
            await machine.transition_to(types["RunStatus"].COMPLETED)

        assert "Invalid transition" in str(exc_info.value)
        assert machine.current_state == types["RunStatus"].CREATED

    @pytest.mark.asyncio
    async def test_created_to_failed_invalid(self):
        """Verify CREATED -> FAILED is invalid."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        with pytest.raises(lifecycle["InvalidTransitionError"]):
            await machine.transition_to(types["RunStatus"].FAILED)

    @pytest.mark.asyncio
    async def test_created_to_awaiting_invalid(self):
        """Verify CREATED -> AWAITING is invalid."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        with pytest.raises(lifecycle["InvalidTransitionError"]):
            await machine.transition_to(types["RunStatus"].AWAITING)

    @pytest.mark.asyncio
    async def test_completed_to_any_state_invalid(self):
        """Verify transitions from COMPLETED (terminal) are invalid."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].COMPLETED
        )

        for target_status in types["RunStatus"]:
            if target_status != types["RunStatus"].COMPLETED:
                with pytest.raises(lifecycle["InvalidTransitionError"]):
                    await machine.transition_to(target_status)

    @pytest.mark.asyncio
    async def test_failed_to_any_state_invalid(self):
        """Verify transitions from FAILED (terminal) are invalid."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].FAILED
        )

        for target_status in types["RunStatus"]:
            if target_status != types["RunStatus"].FAILED:
                with pytest.raises(lifecycle["InvalidTransitionError"]):
                    await machine.transition_to(target_status)

    @pytest.mark.asyncio
    async def test_cancelled_to_any_state_invalid(self):
        """Verify transitions from CANCELLED (terminal) are invalid."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].CANCELLED
        )

        for target_status in types["RunStatus"]:
            if target_status != types["RunStatus"].CANCELLED:
                with pytest.raises(lifecycle["InvalidTransitionError"]):
                    await machine.transition_to(target_status)

    @pytest.mark.asyncio
    async def test_in_progress_to_created_invalid(self):
        """Verify IN_PROGRESS -> CREATED is invalid (no backwards transition)."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].IN_PROGRESS
        )

        with pytest.raises(lifecycle["InvalidTransitionError"]):
            await machine.transition_to(types["RunStatus"].CREATED)

    @pytest.mark.asyncio
    async def test_awaiting_to_completed_invalid(self):
        """Verify AWAITING -> COMPLETED is invalid (must resume first)."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].AWAITING
        )

        with pytest.raises(lifecycle["InvalidTransitionError"]):
            await machine.transition_to(types["RunStatus"].COMPLETED)

    @pytest.mark.asyncio
    async def test_cancelling_to_completed_invalid(self):
        """Verify CANCELLING -> COMPLETED is invalid."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].CANCELLING
        )

        with pytest.raises(lifecycle["InvalidTransitionError"]):
            await machine.transition_to(types["RunStatus"].COMPLETED)

    @pytest.mark.asyncio
    async def test_cancelling_to_in_progress_invalid(self):
        """Verify CANCELLING -> IN_PROGRESS is invalid (cannot resume during cancellation)."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].CANCELLING
        )

        with pytest.raises(lifecycle["InvalidTransitionError"]):
            await machine.transition_to(types["RunStatus"].IN_PROGRESS)


# =============================================================================
# can_transition_to and get_valid_transitions Tests
# =============================================================================

class TestTransitionValidation:
    """Tests for can_transition_to and get_valid_transitions methods."""

    def test_can_transition_to_valid_target(self):
        """Verify can_transition_to returns True for valid transitions."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        assert machine.can_transition_to(types["RunStatus"].IN_PROGRESS) is True
        assert machine.can_transition_to(types["RunStatus"].CANCELLED) is True

    def test_can_transition_to_invalid_target(self):
        """Verify can_transition_to returns False for invalid transitions."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        assert machine.can_transition_to(types["RunStatus"].COMPLETED) is False
        assert machine.can_transition_to(types["RunStatus"].FAILED) is False
        assert machine.can_transition_to(types["RunStatus"].AWAITING) is False

    def test_get_valid_transitions_from_created(self):
        """Verify get_valid_transitions from CREATED state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        valid_transitions = machine.get_valid_transitions()

        assert types["RunStatus"].IN_PROGRESS in valid_transitions
        assert types["RunStatus"].CANCELLED in valid_transitions
        assert len(valid_transitions) == 2

    def test_get_valid_transitions_from_in_progress(self):
        """Verify get_valid_transitions from IN_PROGRESS state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].IN_PROGRESS
        )
        valid_transitions = machine.get_valid_transitions()

        assert types["RunStatus"].COMPLETED in valid_transitions
        assert types["RunStatus"].FAILED in valid_transitions
        assert types["RunStatus"].AWAITING in valid_transitions
        assert types["RunStatus"].CANCELLING in valid_transitions
        assert len(valid_transitions) == 4

    def test_get_valid_transitions_from_awaiting(self):
        """Verify get_valid_transitions from AWAITING state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].AWAITING
        )
        valid_transitions = machine.get_valid_transitions()

        assert types["RunStatus"].IN_PROGRESS in valid_transitions
        assert types["RunStatus"].CANCELLING in valid_transitions
        assert types["RunStatus"].FAILED in valid_transitions
        assert len(valid_transitions) == 3

    def test_get_valid_transitions_from_cancelling(self):
        """Verify get_valid_transitions from CANCELLING state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].CANCELLING
        )
        valid_transitions = machine.get_valid_transitions()

        assert types["RunStatus"].CANCELLED in valid_transitions
        assert len(valid_transitions) == 1

    def test_get_valid_transitions_from_terminal_state(self):
        """Verify get_valid_transitions returns empty list from terminal states."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        for terminal_state in [
            types["RunStatus"].COMPLETED,
            types["RunStatus"].FAILED,
            types["RunStatus"].CANCELLED,
        ]:
            machine = lifecycle["RunStateMachine"](initial_state=terminal_state)
            valid_transitions = machine.get_valid_transitions()
            assert valid_transitions == []


# =============================================================================
# State Transition History Tests
# =============================================================================

class TestStateTransitionHistory:
    """Tests for state transition history tracking."""

    @pytest.mark.asyncio
    async def test_transition_adds_to_history(self):
        """Verify transitions are recorded in history."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        assert len(machine.history) == 1
        assert machine.history[0].from_state == types["RunStatus"].CREATED
        assert machine.history[0].to_state == types["RunStatus"].IN_PROGRESS

    @pytest.mark.asyncio
    async def test_multiple_transitions_recorded(self):
        """Verify multiple transitions are all recorded in order."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].AWAITING)
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].COMPLETED)

        assert len(machine.history) == 4
        assert machine.history[0].to_state == types["RunStatus"].IN_PROGRESS
        assert machine.history[1].to_state == types["RunStatus"].AWAITING
        assert machine.history[2].to_state == types["RunStatus"].IN_PROGRESS
        assert machine.history[3].to_state == types["RunStatus"].COMPLETED

    @pytest.mark.asyncio
    async def test_transition_includes_timestamp(self):
        """Verify transitions include timestamps."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        before = datetime.utcnow()
        transition = await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        after = datetime.utcnow()

        assert transition.timestamp is not None
        assert before <= transition.timestamp <= after

    @pytest.mark.asyncio
    async def test_transition_includes_reason(self):
        """Verify transitions can include a reason."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        transition = await machine.transition_to(
            types["RunStatus"].IN_PROGRESS,
            reason="Starting processing"
        )

        assert transition.reason == "Starting processing"

    @pytest.mark.asyncio
    async def test_transition_includes_metadata(self):
        """Verify transitions can include metadata."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        metadata = {"user_id": "123", "priority": "high"}
        transition = await machine.transition_to(
            types["RunStatus"].IN_PROGRESS,
            metadata=metadata
        )

        assert transition.metadata == metadata
        assert transition.metadata["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_history_is_copy(self):
        """Verify history property returns a copy, not the original."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        history = machine.history
        history.clear()

        assert len(machine.history) == 1

    @pytest.mark.asyncio
    async def test_failed_transition_not_recorded(self):
        """Verify failed transitions are not recorded in history."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        try:
            await machine.transition_to(types["RunStatus"].COMPLETED)
        except lifecycle["InvalidTransitionError"]:
            pass

        assert len(machine.history) == 0


# =============================================================================
# Callback Tests
# =============================================================================

class TestStateCallbacks:
    """Tests for state change callbacks."""

    @pytest.mark.asyncio
    async def test_callback_triggered_on_state_entry(self):
        """Verify callback is triggered when entering a state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        callback = AsyncMock()

        machine.on_state(types["RunStatus"].IN_PROGRESS, callback)
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_receives_transition_info(self):
        """Verify callback receives the StateTransition object."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        received_transition = None

        async def capture_callback(transition):
            nonlocal received_transition
            received_transition = transition

        machine.on_state(types["RunStatus"].IN_PROGRESS, capture_callback)
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        assert received_transition is not None
        assert received_transition.from_state == types["RunStatus"].CREATED
        assert received_transition.to_state == types["RunStatus"].IN_PROGRESS

    @pytest.mark.asyncio
    async def test_multiple_callbacks_for_same_state(self):
        """Verify multiple callbacks can be registered for the same state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        callback1 = AsyncMock()
        callback2 = AsyncMock()

        machine.on_state(types["RunStatus"].IN_PROGRESS, callback1)
        machine.on_state(types["RunStatus"].IN_PROGRESS, callback2)
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        callback1.assert_called_once()
        callback2.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_not_triggered_for_different_state(self):
        """Verify callback is not triggered for different states."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        callback = AsyncMock()

        machine.on_state(types["RunStatus"].COMPLETED, callback)
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_error_does_not_prevent_transition(self):
        """Verify callback errors don't prevent the transition."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        async def failing_callback(transition):
            raise RuntimeError("Callback failed")

        machine.on_state(types["RunStatus"].IN_PROGRESS, failing_callback)
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        # Transition should still succeed
        assert machine.current_state == types["RunStatus"].IN_PROGRESS

    @pytest.mark.asyncio
    async def test_callbacks_triggered_for_terminal_states(self):
        """Verify callbacks work for terminal states."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"](
            initial_state=types["RunStatus"].IN_PROGRESS
        )
        callback = AsyncMock()

        machine.on_state(types["RunStatus"].COMPLETED, callback)
        await machine.transition_to(types["RunStatus"].COMPLETED)

        callback.assert_called_once()


# =============================================================================
# Reset Tests
# =============================================================================

class TestStateMachineReset:
    """Tests for state machine reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_to_default_state(self):
        """Verify reset returns to CREATED state by default."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].COMPLETED)

        machine.reset()

        assert machine.current_state == types["RunStatus"].CREATED

    @pytest.mark.asyncio
    async def test_reset_clears_history(self):
        """Verify reset clears the transition history."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].COMPLETED)

        machine.reset()

        assert machine.history == []

    @pytest.mark.asyncio
    async def test_reset_to_custom_state(self):
        """Verify reset can set a custom initial state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        machine.reset(initial_state=types["RunStatus"].IN_PROGRESS)

        assert machine.current_state == types["RunStatus"].IN_PROGRESS
        assert machine.history == []


# =============================================================================
# Duration Calculation Tests
# =============================================================================

class TestDurationCalculations:
    """Tests for duration and timing calculations."""

    @pytest.mark.asyncio
    async def test_get_duration_returns_none_before_start(self):
        """Verify get_duration returns None if no transitions have occurred."""
        lifecycle = _get_lifecycle()

        machine = lifecycle["RunStateMachine"]()

        assert machine.get_duration() is None

    @pytest.mark.asyncio
    async def test_get_duration_for_completed_run(self):
        """Verify get_duration calculates correct duration for completed run."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].COMPLETED)

        duration = machine.get_duration()

        assert duration is not None
        assert duration >= 0

    @pytest.mark.asyncio
    async def test_get_duration_for_in_progress_run(self):
        """Verify get_duration returns ongoing duration for in-progress run."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        duration = machine.get_duration()

        assert duration is not None
        assert duration >= 0

    @pytest.mark.asyncio
    async def test_get_time_in_state_for_single_visit(self):
        """Verify get_time_in_state for a state visited once."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].COMPLETED)

        time_in_progress = machine.get_time_in_state(types["RunStatus"].IN_PROGRESS)

        assert time_in_progress >= 0

    @pytest.mark.asyncio
    async def test_get_time_in_state_for_multiple_visits(self):
        """Verify get_time_in_state accumulates time for multiple visits."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].AWAITING)
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].COMPLETED)

        time_in_progress = machine.get_time_in_state(types["RunStatus"].IN_PROGRESS)

        assert time_in_progress >= 0

    @pytest.mark.asyncio
    async def test_get_time_in_state_for_current_state(self):
        """Verify get_time_in_state includes time in current state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        # Still in IN_PROGRESS state
        time_in_progress = machine.get_time_in_state(types["RunStatus"].IN_PROGRESS)

        assert time_in_progress >= 0

    @pytest.mark.asyncio
    async def test_get_time_in_state_never_entered(self):
        """Verify get_time_in_state returns 0 for states never entered."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].COMPLETED)

        time_in_awaiting = machine.get_time_in_state(types["RunStatus"].AWAITING)

        assert time_in_awaiting == 0.0


# =============================================================================
# StateTransition Dataclass Tests
# =============================================================================

class TestStateTransition:
    """Tests for StateTransition dataclass."""

    def test_state_transition_creation(self):
        """Verify StateTransition can be created with required fields."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        transition = lifecycle["StateTransition"](
            from_state=types["RunStatus"].CREATED,
            to_state=types["RunStatus"].IN_PROGRESS,
            timestamp=datetime.utcnow(),
        )

        assert transition.from_state == types["RunStatus"].CREATED
        assert transition.to_state == types["RunStatus"].IN_PROGRESS
        assert transition.reason is None
        assert transition.metadata is None

    def test_state_transition_with_all_fields(self):
        """Verify StateTransition can be created with all fields."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        timestamp = datetime.utcnow()
        metadata = {"key": "value"}

        transition = lifecycle["StateTransition"](
            from_state=types["RunStatus"].IN_PROGRESS,
            to_state=types["RunStatus"].FAILED,
            timestamp=timestamp,
            reason="Error occurred",
            metadata=metadata,
        )

        assert transition.from_state == types["RunStatus"].IN_PROGRESS
        assert transition.to_state == types["RunStatus"].FAILED
        assert transition.timestamp == timestamp
        assert transition.reason == "Error occurred"
        assert transition.metadata == metadata


# =============================================================================
# Full Lifecycle Scenario Tests
# =============================================================================

class TestFullLifecycleScenarios:
    """Tests for complete lifecycle scenarios."""

    @pytest.mark.asyncio
    async def test_successful_run_lifecycle(self):
        """Test a successful run: CREATED -> IN_PROGRESS -> COMPLETED."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        # Start the run
        await machine.transition_to(
            types["RunStatus"].IN_PROGRESS,
            reason="Processing started"
        )
        assert machine.current_state == types["RunStatus"].IN_PROGRESS

        # Complete the run
        await machine.transition_to(
            types["RunStatus"].COMPLETED,
            reason="Processing finished"
        )
        assert machine.current_state == types["RunStatus"].COMPLETED
        assert machine.is_terminal is True
        assert len(machine.history) == 2

    @pytest.mark.asyncio
    async def test_failed_run_lifecycle(self):
        """Test a failed run: CREATED -> IN_PROGRESS -> FAILED."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(
            types["RunStatus"].FAILED,
            reason="Internal error",
            metadata={"error_code": "E001"}
        )

        assert machine.current_state == types["RunStatus"].FAILED
        assert machine.is_terminal is True
        assert machine.history[-1].metadata["error_code"] == "E001"

    @pytest.mark.asyncio
    async def test_awaiting_and_resume_lifecycle(self):
        """Test await/resume flow: CREATED -> IN_PROGRESS -> AWAITING -> IN_PROGRESS -> COMPLETED."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(
            types["RunStatus"].AWAITING,
            reason="Waiting for user input"
        )
        assert machine.current_state == types["RunStatus"].AWAITING

        await machine.transition_to(
            types["RunStatus"].IN_PROGRESS,
            reason="User provided input"
        )
        assert machine.current_state == types["RunStatus"].IN_PROGRESS

        await machine.transition_to(types["RunStatus"].COMPLETED)
        assert machine.current_state == types["RunStatus"].COMPLETED
        assert len(machine.history) == 4

    @pytest.mark.asyncio
    async def test_cancellation_during_progress(self):
        """Test cancellation: IN_PROGRESS -> CANCELLING -> CANCELLED."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(
            types["RunStatus"].CANCELLING,
            reason="User requested cancellation"
        )
        await machine.transition_to(types["RunStatus"].CANCELLED)

        assert machine.current_state == types["RunStatus"].CANCELLED
        assert machine.is_terminal is True

    @pytest.mark.asyncio
    async def test_cancellation_during_await(self):
        """Test cancellation while awaiting: AWAITING -> CANCELLING -> CANCELLED."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].AWAITING)
        await machine.transition_to(types["RunStatus"].CANCELLING)
        await machine.transition_to(types["RunStatus"].CANCELLED)

        assert machine.current_state == types["RunStatus"].CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_before_start(self):
        """Test immediate cancellation: CREATED -> CANCELLED."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        await machine.transition_to(
            types["RunStatus"].CANCELLED,
            reason="Cancelled before starting"
        )

        assert machine.current_state == types["RunStatus"].CANCELLED
        assert len(machine.history) == 1

    @pytest.mark.asyncio
    async def test_await_timeout_failure(self):
        """Test await timeout: AWAITING -> FAILED."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].AWAITING)
        await machine.transition_to(
            types["RunStatus"].FAILED,
            reason="Await timeout exceeded"
        )

        assert machine.current_state == types["RunStatus"].FAILED


# =============================================================================
# RunLifecycleManager Tests
# =============================================================================

class TestRunLifecycleManager:
    """Tests for RunLifecycleManager high-level operations."""

    def test_create_machine(self):
        """Verify creating a new state machine for a run."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        manager = lifecycle["RunLifecycleManager"]()
        machine = manager.create_machine("run-123")

        assert machine is not None
        assert machine.current_state == types["RunStatus"].CREATED

    def test_get_machine(self):
        """Verify getting an existing state machine."""
        lifecycle = _get_lifecycle()

        manager = lifecycle["RunLifecycleManager"]()
        manager.create_machine("run-123")

        machine = manager.get_machine("run-123")
        assert machine is not None

    def test_get_nonexistent_machine(self):
        """Verify getting a non-existent machine returns None."""
        lifecycle = _get_lifecycle()

        manager = lifecycle["RunLifecycleManager"]()

        machine = manager.get_machine("nonexistent")
        assert machine is None

    def test_remove_machine(self):
        """Verify removing a state machine."""
        lifecycle = _get_lifecycle()

        manager = lifecycle["RunLifecycleManager"]()
        manager.create_machine("run-123")

        removed = manager.remove_machine("run-123")
        assert removed is True
        assert manager.get_machine("run-123") is None

    def test_remove_nonexistent_machine(self):
        """Verify removing a non-existent machine returns False."""
        lifecycle = _get_lifecycle()

        manager = lifecycle["RunLifecycleManager"]()

        removed = manager.remove_machine("nonexistent")
        assert removed is False

    @pytest.mark.asyncio
    async def test_start_run(self):
        """Verify start_run helper method."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        manager = lifecycle["RunLifecycleManager"]()
        manager.create_machine("run-123")

        transition = await manager.start_run("run-123", reason="Starting")

        machine = manager.get_machine("run-123")
        assert machine.current_state == types["RunStatus"].IN_PROGRESS
        assert transition.to_state == types["RunStatus"].IN_PROGRESS

    @pytest.mark.asyncio
    async def test_start_run_nonexistent(self):
        """Verify start_run raises error for non-existent run."""
        lifecycle = _get_lifecycle()

        manager = lifecycle["RunLifecycleManager"]()

        with pytest.raises(ValueError, match="No state machine"):
            await manager.start_run("nonexistent")

    @pytest.mark.asyncio
    async def test_complete_run(self):
        """Verify complete_run helper method."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        manager = lifecycle["RunLifecycleManager"]()
        machine = manager.create_machine("run-123")
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        transition = await manager.complete_run("run-123", reason="Done")

        assert machine.current_state == types["RunStatus"].COMPLETED

    @pytest.mark.asyncio
    async def test_fail_run(self):
        """Verify fail_run helper method."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        manager = lifecycle["RunLifecycleManager"]()
        machine = manager.create_machine("run-123")
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        transition = await manager.fail_run("run-123", reason="Error occurred")

        assert machine.current_state == types["RunStatus"].FAILED
        assert transition.reason == "Error occurred"

    @pytest.mark.asyncio
    async def test_await_input(self):
        """Verify await_input helper method."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        manager = lifecycle["RunLifecycleManager"]()
        machine = manager.create_machine("run-123")
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        transition = await manager.await_input("run-123", reason="Need input")

        assert machine.current_state == types["RunStatus"].AWAITING

    @pytest.mark.asyncio
    async def test_resume_run(self):
        """Verify resume_run helper method."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        manager = lifecycle["RunLifecycleManager"]()
        machine = manager.create_machine("run-123")
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].AWAITING)

        transition = await manager.resume_run("run-123", reason="Input received")

        assert machine.current_state == types["RunStatus"].IN_PROGRESS

    @pytest.mark.asyncio
    async def test_cancel_run(self):
        """Verify cancel_run helper method transitions through CANCELLING."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        manager = lifecycle["RunLifecycleManager"]()
        machine = manager.create_machine("run-123")
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        transition = await manager.cancel_run("run-123", reason="User cancelled")

        assert machine.current_state == types["RunStatus"].CANCELLED
        # Should have two transitions: IN_PROGRESS -> CANCELLING -> CANCELLED
        assert len(machine.history) == 3

    @pytest.mark.asyncio
    async def test_cancel_run_from_cancelling(self):
        """Verify cancel_run when already in CANCELLING state."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        manager = lifecycle["RunLifecycleManager"]()
        machine = manager.create_machine("run-123")
        await machine.transition_to(types["RunStatus"].IN_PROGRESS)
        await machine.transition_to(types["RunStatus"].CANCELLING)

        transition = await manager.cancel_run("run-123")

        assert machine.current_state == types["RunStatus"].CANCELLED

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_manager(self):
        """Test full lifecycle using manager methods."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        manager = lifecycle["RunLifecycleManager"]()
        manager.create_machine("run-123")

        await manager.start_run("run-123")
        machine = manager.get_machine("run-123")
        assert machine.current_state == types["RunStatus"].IN_PROGRESS

        await manager.await_input("run-123")
        assert machine.current_state == types["RunStatus"].AWAITING

        await manager.resume_run("run-123")
        assert machine.current_state == types["RunStatus"].IN_PROGRESS

        await manager.complete_run("run-123")
        assert machine.current_state == types["RunStatus"].COMPLETED

        # Clean up
        manager.remove_machine("run-123")
        assert manager.get_machine("run-123") is None


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCasesAndErrorHandling:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_transition_to_same_state_invalid(self):
        """Verify transitioning to the same state is invalid."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        with pytest.raises(lifecycle["InvalidTransitionError"]):
            await machine.transition_to(types["RunStatus"].CREATED)

    @pytest.mark.asyncio
    async def test_concurrent_callbacks(self):
        """Verify callbacks run sequentially for a single transition."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()
        call_order = []

        async def callback1(transition):
            call_order.append(1)
            await asyncio.sleep(0.01)
            call_order.append(2)

        async def callback2(transition):
            call_order.append(3)

        machine.on_state(types["RunStatus"].IN_PROGRESS, callback1)
        machine.on_state(types["RunStatus"].IN_PROGRESS, callback2)

        await machine.transition_to(types["RunStatus"].IN_PROGRESS)

        # Callbacks should run in sequence
        assert call_order == [1, 2, 3]

    def test_valid_transitions_constant_is_correct(self):
        """Verify VALID_TRANSITIONS set contains expected transitions."""
        lifecycle = _get_lifecycle()
        types = _get_types()
        RunStateMachine = lifecycle["RunStateMachine"]

        # Check some key transitions exist
        assert (types["RunStatus"].CREATED, types["RunStatus"].IN_PROGRESS) in RunStateMachine.VALID_TRANSITIONS
        assert (types["RunStatus"].IN_PROGRESS, types["RunStatus"].COMPLETED) in RunStateMachine.VALID_TRANSITIONS
        assert (types["RunStatus"].CANCELLING, types["RunStatus"].CANCELLED) in RunStateMachine.VALID_TRANSITIONS

        # Check some invalid transitions don't exist
        assert (types["RunStatus"].CREATED, types["RunStatus"].COMPLETED) not in RunStateMachine.VALID_TRANSITIONS
        assert (types["RunStatus"].COMPLETED, types["RunStatus"].CREATED) not in RunStateMachine.VALID_TRANSITIONS

    def test_terminal_states_constant_is_correct(self):
        """Verify TERMINAL_STATES set contains expected states."""
        lifecycle = _get_lifecycle()
        types = _get_types()
        RunStateMachine = lifecycle["RunStateMachine"]

        assert types["RunStatus"].COMPLETED in RunStateMachine.TERMINAL_STATES
        assert types["RunStatus"].FAILED in RunStateMachine.TERMINAL_STATES
        assert types["RunStatus"].CANCELLED in RunStateMachine.TERMINAL_STATES
        assert len(RunStateMachine.TERMINAL_STATES) == 3

        # Non-terminal states should not be in the set
        assert types["RunStatus"].CREATED not in RunStateMachine.TERMINAL_STATES
        assert types["RunStatus"].IN_PROGRESS not in RunStateMachine.TERMINAL_STATES
        assert types["RunStatus"].AWAITING not in RunStateMachine.TERMINAL_STATES
        assert types["RunStatus"].CANCELLING not in RunStateMachine.TERMINAL_STATES

    @pytest.mark.asyncio
    async def test_error_message_includes_valid_transitions(self):
        """Verify InvalidTransitionError message includes valid transitions."""
        lifecycle = _get_lifecycle()
        types = _get_types()

        machine = lifecycle["RunStateMachine"]()

        with pytest.raises(lifecycle["InvalidTransitionError"]) as exc_info:
            await machine.transition_to(types["RunStatus"].COMPLETED)

        error_message = str(exc_info.value)
        assert "Valid transitions" in error_message
        assert "in-progress" in error_message or "IN_PROGRESS" in error_message
