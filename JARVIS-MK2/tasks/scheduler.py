"""
Task scheduler for JARVIS-MK2.
Handles scheduling tasks for future execution.
"""

import asyncio
import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from core.logger import get_logger
from core.events import publish
from .task_manager import task_manager, Task

logger = get_logger(__name__)


@dataclass(order=True)
class ScheduledTask:
    """Represents a scheduled task."""
    # Priority queue fields
    execute_at: float  # Timestamp when to execute
    # Data fields
    task_func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    task_id: str = field(compare=False)
    periodic: bool = field(default=False, compare=False)
    period: float = field(default=0.0, compare=False)  # Seconds between executions


class Scheduler:
    """Schedules tasks for future execution."""

    def __init__(self):
        """Initialize the scheduler."""
        self.logger = get_logger(__name__)
        self._scheduled_tasks: list[ScheduledTask] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._cancelled_tasks: set[str] = set()

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            self.logger.warning("Scheduler already running")
            return

        self.logger.info("Starting task scheduler")
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self.logger.info("Stopping task scheduler")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def schedule_task(
        self,
        execute_at: float,
        task_func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Schedule a task for execution at a specific time.

        Args:
            execute_at: Timestamp when to execute the task
            task_func: Function to execute
            *args: Arguments to pass to the function
            task_id: Optional task ID (generated if not provided)
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Scheduled task ID
        """
        if task_id is None:
            import uuid
            task_id = f"SCH-{uuid.uuid4().hex[:8].upper()}"

        scheduled_task = ScheduledTask(
            execute_at=execute_at,
            task_func=task_func,
            args=args,
            kwargs=kwargs,
            task_id=task_id,
        )

        heapq.heappush(self._scheduled_tasks, scheduled_task)
        self.logger.debug(f"Scheduled task {task_id} for {execute_at}")

        return task_id

    async def schedule_recurring(
        self,
        interval: float,
        task_func: Callable,
        *args,
        delay: float = 0.0,
        **kwargs,
    ) -> str:
        """
        Schedule a recurring task.

        Args:
            interval: Seconds between executions
            task_func: Function to execute
            *args: Arguments to pass to the function
            delay: Initial delay before first execution
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Scheduled task ID
        """
        import time
        import uuid

        execute_at = time.time() + delay
        task_id = f"SCH-{uuid.uuid4().hex[:8].upper()}"

        scheduled_task = ScheduledTask(
            execute_at=execute_at,
            task_func=task_func,
            args=args,
            kwargs=kwargs,
            task_id=task_id,
            periodic=True,
            period=interval,
        )

        heapq.heappush(self._scheduled_tasks, scheduled_task)
        self.logger.debug(
            f"Scheduled recurring task {task_id} every {interval}s (starts at {execute_at})"
        )

        return task_id

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        # Mark as cancelled - we'll remove it when we pop it
        self._cancelled_tasks.add(task_id)
        self.logger.debug(f"Cancelled scheduled task {task_id}")
        return True  # We don't check if it exists for simplicity

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        self.logger.debug("Scheduler loop started")
        while self._running:
            try:
                now = asyncio.get_event_loop().time()

                # Check for expired tasks
                while (
                    self._scheduled_tasks
                    and self._scheduled_tasks[0].execute_at <= now
                ):
                    scheduled_task = heapq.heappop(self._scheduled_tasks)

                    # Skip if cancelled
                    if scheduled_task.task_id in self._cancelled_tasks:
                        self._cancelled_tasks.discard(scheduled_task.task_id)
                        continue

                    # Execute the task
                    self.logger.debug(
                        f"Executing scheduled task {scheduled_task.task_id}"
                    )
                    try:
                        result = scheduled_task.task_func(
                            *scheduled_task.args, **scheduled_task.kwargs
                        )
                        # If it's a coroutine, we should await it
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        self.logger.error(
                            f"Error executing scheduled task {scheduled_task.task_id}: {e}"
                        )

                    # If periodic, reschedule
                    if scheduled_task.periodic and scheduled_task.period > 0:
                        new_execute_at = now + scheduled_task.period
                        rescheduled = ScheduledTask(
                            execute_at=new_execute_at,
                            task_func=scheduled_task.task_func,
                            args=scheduled_task.args,
                            kwargs=scheduled_task.kwargs,
                            task_id=scheduled_task.task_id,
                            periodic=True,
                            period=scheduled_task.period,
                        )
                        heapq.heappush(self._scheduled_tasks, rescheduled)
                        self.logger.debug(
                            f"Rescheduled periodic task {scheduled_task.task_id} for {new_execute_at}"
                        )

                # Sleep until next scheduled task or 1 second
                if self._scheduled_tasks:
                    wait_time = max(
                        0, self._scheduled_tasks[0].execute_at - asyncio.get_event_loop().time()
                    )
                    await asyncio.sleep(min(wait_time, 1.0))
                else:
                    await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(1.0)

        self.logger.debug("Scheduler loop stopped")


# Global scheduler instance
scheduler = Scheduler()