"""
ACP Run Lifecycle State Machine

Provides state machine implementation for managing run lifecycle transitions.
"""

from dataclasses import dataclass
from typing import Callable, Awaitable
from datetime import datetime

from loguru import logger

from app.acp.core.types import RunStatus


@dataclass
class StateTransition:
    """Represents a state transition in the run lifecycle."""

    from_state: RunStatus
    to_state: RunStatus
    timestamp: datetime
    reason: str | None = None
    metadata: dict | None = None


class RunStateMachine:
    """
    State machine for managing run lifecycle transitions.

    Enforces valid state transitions according to the ACP specification:
        created -> in_progress -> completed
                              -> failed
                              -> awaiting (pause for external info)
                              -> cancelling -> cancelled

    Provides:
    - State transition validation
    - Transition history tracking
    - Event callbacks for state changes
    """

    # Valid state transitions as (from_state, to_state) pairs
    VALID_TRANSITIONS: set[tuple[RunStatus, RunStatus]] = {
        # From CREATED
        (RunStatus.CREATED, RunStatus.IN_PROGRESS),
        (RunStatus.CREATED, RunStatus.CANCELLED),  # Can cancel before starting

        # From IN_PROGRESS
        (RunStatus.IN_PROGRESS, RunStatus.COMPLETED),
        (RunStatus.IN_PROGRESS, RunStatus.FAILED),
        (RunStatus.IN_PROGRESS, RunStatus.AWAITING),
        (RunStatus.IN_PROGRESS, RunStatus.CANCELLING),

        # From AWAITING
        (RunStatus.AWAITING, RunStatus.IN_PROGRESS),  # Resume
        (RunStatus.AWAITING, RunStatus.CANCELLING),
        (RunStatus.AWAITING, RunStatus.FAILED),  # Timeout

        # From CANCELLING
        (RunStatus.CANCELLING, RunStatus.CANCELLED),
    }

    # Terminal states (no further transitions allowed)
    TERMINAL_STATES: set[RunStatus] = {
        RunStatus.COMPLETED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    }

    def __init__(self, initial_state: RunStatus = RunStatus.CREATED):
        """
        Initialize the state machine.

        Args:
            initial_state: Starting state (default: CREATED)
        """
        self._current_state = initial_state
        self._history: list[StateTransition] = []
        self._callbacks: dict[RunStatus, list[Callable[[StateTransition], Awaitable[None]]]] = {}

    @property
    def current_state(self) -> RunStatus:
        """Get the current state."""
        return self._current_state

    @property
    def history(self) -> list[StateTransition]:
        """Get the transition history."""
        return self._history.copy()

    @property
    def is_terminal(self) -> bool:
        """Check if the current state is terminal."""
        return self._current_state in self.TERMINAL_STATES

    def can_transition_to(self, target_state: RunStatus) -> bool:
        """
        Check if a transition to the target state is valid.

        Args:
            target_state: The desired target state

        Returns:
            True if the transition is valid
        """
        return (self._current_state, target_state) in self.VALID_TRANSITIONS

    def get_valid_transitions(self) -> list[RunStatus]:
        """
        Get all valid target states from the current state.

        Returns:
            List of valid target states
        """
        return [
            to_state
            for (from_state, to_state) in self.VALID_TRANSITIONS
            if from_state == self._current_state
        ]

    async def transition_to(
        self,
        target_state: RunStatus,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> StateTransition:
        """
        Transition to a new state.

        Args:
            target_state: The target state
            reason: Optional reason for the transition
            metadata: Optional metadata

        Returns:
            The state transition record

        Raises:
            InvalidTransitionError: If the transition is not valid
        """
        if not self.can_transition_to(target_state):
            raise InvalidTransitionError(
                f"Invalid transition from {self._current_state} to {target_state}. "
                f"Valid transitions: {self.get_valid_transitions()}"
            )

        transition = StateTransition(
            from_state=self._current_state,
            to_state=target_state,
            timestamp=datetime.utcnow(),
            reason=reason,
            metadata=metadata,
        )

        self._current_state = target_state
        self._history.append(transition)

        logger.debug(
            f"State transition: {transition.from_state} -> {transition.to_state}"
            f"{f' ({reason})' if reason else ''}"
        )

        # Trigger callbacks
        await self._trigger_callbacks(transition)

        return transition

    def on_state(
        self,
        state: RunStatus,
        callback: Callable[[StateTransition], Awaitable[None]],
    ) -> None:
        """
        Register a callback for entering a specific state.

        Args:
            state: The state to watch
            callback: Async callback function
        """
        if state not in self._callbacks:
            self._callbacks[state] = []
        self._callbacks[state].append(callback)

    async def _trigger_callbacks(self, transition: StateTransition) -> None:
        """Trigger callbacks for the new state."""
        callbacks = self._callbacks.get(transition.to_state, [])
        for callback in callbacks:
            try:
                await callback(transition)
            except Exception as e:
                logger.error(f"State callback error: {e}")

    def reset(self, initial_state: RunStatus = RunStatus.CREATED) -> None:
        """
        Reset the state machine.

        Args:
            initial_state: State to reset to
        """
        self._current_state = initial_state
        self._history.clear()

    def get_duration(self) -> float | None:
        """
        Get the total run duration in seconds.

        Returns:
            Duration in seconds or None if not started
        """
        if len(self._history) < 1:
            return None

        first_transition = self._history[0]

        if self.is_terminal:
            last_transition = self._history[-1]
            return (last_transition.timestamp - first_transition.timestamp).total_seconds()

        return (datetime.utcnow() - first_transition.timestamp).total_seconds()

    def get_time_in_state(self, state: RunStatus) -> float:
        """
        Get total time spent in a specific state.

        Args:
            state: The state to measure

        Returns:
            Time in seconds
        """
        total = 0.0

        for i, transition in enumerate(self._history):
            if transition.to_state == state:
                # Find the next transition out of this state
                if i + 1 < len(self._history):
                    next_transition = self._history[i + 1]
                    total += (next_transition.timestamp - transition.timestamp).total_seconds()
                elif self._current_state == state:
                    # Still in this state
                    total += (datetime.utcnow() - transition.timestamp).total_seconds()

        return total


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


class RunLifecycleManager:
    """
    High-level manager for run lifecycle operations.

    Provides convenient methods for common lifecycle operations.
    """

    def __init__(self):
        """Initialize the lifecycle manager."""
        self._machines: dict[str, RunStateMachine] = {}

    def create_machine(self, run_id: str) -> RunStateMachine:
        """
        Create a new state machine for a run.

        Args:
            run_id: Unique run identifier

        Returns:
            New state machine
        """
        machine = RunStateMachine()
        self._machines[run_id] = machine
        return machine

    def get_machine(self, run_id: str) -> RunStateMachine | None:
        """
        Get the state machine for a run.

        Args:
            run_id: The run ID

        Returns:
            State machine or None
        """
        return self._machines.get(run_id)

    def remove_machine(self, run_id: str) -> bool:
        """
        Remove a state machine.

        Args:
            run_id: The run ID

        Returns:
            True if removed
        """
        if run_id in self._machines:
            del self._machines[run_id]
            return True
        return False

    async def start_run(self, run_id: str, reason: str | None = None) -> StateTransition:
        """
        Start a run (CREATED -> IN_PROGRESS).

        Args:
            run_id: The run ID
            reason: Optional reason

        Returns:
            The transition
        """
        machine = self.get_machine(run_id)
        if not machine:
            raise ValueError(f"No state machine for run {run_id}")

        return await machine.transition_to(RunStatus.IN_PROGRESS, reason=reason)

    async def complete_run(self, run_id: str, reason: str | None = None) -> StateTransition:
        """
        Complete a run (IN_PROGRESS -> COMPLETED).

        Args:
            run_id: The run ID
            reason: Optional reason

        Returns:
            The transition
        """
        machine = self.get_machine(run_id)
        if not machine:
            raise ValueError(f"No state machine for run {run_id}")

        return await machine.transition_to(RunStatus.COMPLETED, reason=reason)

    async def fail_run(self, run_id: str, reason: str) -> StateTransition:
        """
        Fail a run (IN_PROGRESS/AWAITING -> FAILED).

        Args:
            run_id: The run ID
            reason: Error reason

        Returns:
            The transition
        """
        machine = self.get_machine(run_id)
        if not machine:
            raise ValueError(f"No state machine for run {run_id}")

        return await machine.transition_to(RunStatus.FAILED, reason=reason)

    async def await_input(self, run_id: str, reason: str | None = None) -> StateTransition:
        """
        Pause for input (IN_PROGRESS -> AWAITING).

        Args:
            run_id: The run ID
            reason: Optional reason

        Returns:
            The transition
        """
        machine = self.get_machine(run_id)
        if not machine:
            raise ValueError(f"No state machine for run {run_id}")

        return await machine.transition_to(RunStatus.AWAITING, reason=reason)

    async def resume_run(self, run_id: str, reason: str | None = None) -> StateTransition:
        """
        Resume a run (AWAITING -> IN_PROGRESS).

        Args:
            run_id: The run ID
            reason: Optional reason

        Returns:
            The transition
        """
        machine = self.get_machine(run_id)
        if not machine:
            raise ValueError(f"No state machine for run {run_id}")

        return await machine.transition_to(RunStatus.IN_PROGRESS, reason=reason)

    async def cancel_run(self, run_id: str, reason: str | None = None) -> StateTransition:
        """
        Cancel a run (any -> CANCELLING -> CANCELLED).

        Args:
            run_id: The run ID
            reason: Optional reason

        Returns:
            The final transition
        """
        machine = self.get_machine(run_id)
        if not machine:
            raise ValueError(f"No state machine for run {run_id}")

        # First transition to CANCELLING if not already
        if machine.current_state != RunStatus.CANCELLING:
            await machine.transition_to(RunStatus.CANCELLING, reason=reason)

        # Then complete the cancellation
        return await machine.transition_to(RunStatus.CANCELLED, reason=reason)
