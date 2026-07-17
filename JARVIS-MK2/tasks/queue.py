"""
Task queue for JARVIS-MK2.
Provides asynchronous task processing capabilities.
"""

import asyncio
from collections import deque
from typing import Any, Callable, Deque, Optional

from core.logger import get_logger
from core.events import publish
from .task_manager import Task, task_manager

logger = get_logger(__name__)


class TaskQueue:
    """Asynchronous task queue for processing tasks."""

    def __init__(self, max_size: int = 100):
        """
        Initialize the task queue.

        Args:
            max_size: Maximum number of tasks in the queue
        """
        self.logger = get_logger(__name__)
        self._queue: Deque[tuple[Callable, tuple, dict]] = deque(maxlen=max_size)
        self._processing = False
        self._worker_task: Optional[asyncio.Task] = None
        self._result_futures: dict[str, asyncio.Future] = {}

    async def start(self) -> None:
        """Start the queue processor."""
        if self._processing:
            self.logger.warning("Task queue already started")
            return

        self.logger.info("Starting task queue")
        self._processing = True
        self._worker_task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        """Stop the queue processor."""
        if not self._processing:
            return

        self.logger.info("Stopping task queue")
        self._processing = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def put(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Add a task to the queue.

        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            task_id: Optional task ID for tracking
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Task ID
        """
        if task_id is None:
            import uuid
            task_id = f"Q-{uuid.uuid4().hex[:8].upper()}"

        # Create a future for the result if we want to wait for it
        future = asyncio.Future()
        self._result_futures[task_id] = future

        # Add to queue
        self._queue.append((func, args, kwargs, task_id))
        self.logger.debug(f"Added task {task_id} to queue")

        return task_id

    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        Get the result of a queued task.

        Args:
            task_id: Task ID
            timeout: Maximum time to wait for result

        Returns:
            Task result

        Raises:
            asyncio.TimeoutError: If timeout is reached
            Exception: If the task failed
        """
        future = self._result_futures.get(task_id)
        if not future:
            raise ValueError(f"No future found for task {task_id}")

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise
        finally:
            # Clean up
            self._result_futures.pop(task_id, None)

    async def _process_queue(self) -> None:
        """Process tasks in the queue."""
        self.logger.debug("Task queue processor started")
        while self._processing:
            try:
                # Wait for a task to become available
                if not self._queue:
                    await asyncio.sleep(0.1)
                    continue

                # Get the next task
                func, args, kwargs, task_id = self._queue.popleft()

                # Process the task
                try:
                    self.logger.debug(f"Processing queued task {task_id}")
                    result = func(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        result = await result

                    # Set the result
                    if task_id in self._result_futures:
                        self._result_futures[task_id].set_result(result)

                    # Publish success event
                    publish("task.queue_success", {"task_id": task_id}, source="TaskQueue")

                except Exception as e:
                    self.logger.error(f"Error processing queued task {task_id}: {e}")
                    if task_id in self._result_futures:
                        self._result_futures[task_id].set_exception(e)

                    # Publish failure event
                    publish(
                        "task.queue_failure",
                        {"task_id": task_id, "error": str(e)},
                        source="TaskQueue",
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in task queue processor: {e}")
                await asyncio.sleep(1.0)

        self.logger.debug("Task queue processor stopped")


# Global task queue instance
task_queue = TaskQueue()