"""
ACP Run Manager

Provides run management functionality for the ACP client.
"""

from typing import Any, Callable, Awaitable
from uuid import UUID
import asyncio

from loguru import logger

from app.acp.core.models import Message, Run
from app.acp.core.types import RunStatus
from app.acp.core.schemas import RunResponse


class RunManager:
    """
    Manager for ACP run operations.

    Provides:
    - Run status polling
    - Batch run management
    - Run lifecycle callbacks
    """

    def __init__(self):
        """Initialize the run manager."""
        self._active_runs: dict[UUID, RunResponse] = {}
        self._callbacks: dict[str, list[Callable[[RunResponse], Awaitable[None]]]] = {
            "on_start": [],
            "on_complete": [],
            "on_fail": [],
            "on_await": [],
        }

    def on_start(
        self,
        callback: Callable[[RunResponse], Awaitable[None]],
    ) -> None:
        """Register a callback for when runs start."""
        self._callbacks["on_start"].append(callback)

    def on_complete(
        self,
        callback: Callable[[RunResponse], Awaitable[None]],
    ) -> None:
        """Register a callback for when runs complete."""
        self._callbacks["on_complete"].append(callback)

    def on_fail(
        self,
        callback: Callable[[RunResponse], Awaitable[None]],
    ) -> None:
        """Register a callback for when runs fail."""
        self._callbacks["on_fail"].append(callback)

    def on_await(
        self,
        callback: Callable[[RunResponse], Awaitable[None]],
    ) -> None:
        """Register a callback for when runs enter awaiting state."""
        self._callbacks["on_await"].append(callback)

    async def _trigger_callbacks(
        self,
        event: str,
        response: RunResponse,
    ) -> None:
        """Trigger callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                await callback(response)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    def track_run(self, response: RunResponse) -> None:
        """
        Add a run to tracking.

        Args:
            response: The run response to track
        """
        self._active_runs[response.run_id] = response

    def untrack_run(self, run_id: UUID) -> None:
        """
        Remove a run from tracking.

        Args:
            run_id: The run ID to untrack
        """
        self._active_runs.pop(run_id, None)

    def get_tracked_run(self, run_id: UUID) -> RunResponse | None:
        """
        Get a tracked run by ID.

        Args:
            run_id: The run ID

        Returns:
            RunResponse or None
        """
        return self._active_runs.get(run_id)

    def get_active_runs(self) -> list[RunResponse]:
        """Get all actively tracked runs."""
        return list(self._active_runs.values())

    def get_runs_by_status(self, status: RunStatus) -> list[RunResponse]:
        """Get runs with a specific status."""
        return [r for r in self._active_runs.values() if r.status == status]

    async def update_run_status(
        self,
        run_id: UUID,
        response: RunResponse,
    ) -> None:
        """
        Update a run's status and trigger appropriate callbacks.

        Args:
            run_id: The run ID
            response: Updated run response
        """
        previous = self._active_runs.get(run_id)
        self._active_runs[run_id] = response

        # Trigger callbacks based on status change
        if previous and previous.status != response.status:
            if response.status == RunStatus.IN_PROGRESS:
                await self._trigger_callbacks("on_start", response)
            elif response.status == RunStatus.COMPLETED:
                await self._trigger_callbacks("on_complete", response)
                self.untrack_run(run_id)
            elif response.status == RunStatus.FAILED:
                await self._trigger_callbacks("on_fail", response)
                self.untrack_run(run_id)
            elif response.status == RunStatus.AWAITING:
                await self._trigger_callbacks("on_await", response)


class BatchRunManager:
    """
    Manager for batch run operations.

    Allows running multiple agents concurrently and collecting results.
    """

    def __init__(self, max_concurrent: int = 10):
        """
        Initialize the batch manager.

        Args:
            max_concurrent: Maximum concurrent runs
        """
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def run_batch(
        self,
        run_func: Callable[[Any], Awaitable[RunResponse]],
        inputs: list[Any],
    ) -> list[RunResponse]:
        """
        Run a batch of agent calls concurrently.

        Args:
            run_func: Function to call for each input
            inputs: List of inputs

        Returns:
            List of RunResponses (in same order as inputs)
        """

        async def bounded_run(input_data: Any) -> RunResponse:
            async with self._semaphore:
                return await run_func(input_data)

        tasks = [bounded_run(inp) for inp in inputs]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def run_sequential(
        self,
        run_func: Callable[[Any], Awaitable[RunResponse]],
        inputs: list[Any],
        stop_on_error: bool = False,
    ) -> list[RunResponse]:
        """
        Run agents sequentially.

        Args:
            run_func: Function to call for each input
            inputs: List of inputs
            stop_on_error: Whether to stop on first error

        Returns:
            List of RunResponses
        """
        results = []
        for inp in inputs:
            try:
                result = await run_func(inp)
                results.append(result)

                if stop_on_error and result.status == RunStatus.FAILED:
                    break
            except Exception as e:
                logger.error(f"Batch run error: {e}")
                if stop_on_error:
                    break

        return results
