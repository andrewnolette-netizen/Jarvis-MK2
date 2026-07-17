"""
Executor for JARVIS-MK2.
Responsible for executing tasks, handling retries, emitting events, logging results, and updating memory.
"""

import asyncio
import time
import random
from typing import Any, Dict, Optional

from core.logger import get_logger
from core.events import publish
from tasks.task_manager import TaskManager, TaskStatus, Task
from memory.memory_manager import memory_manager

logger = get_logger(__name__)


class Executor:
    """Executes tasks and manages their lifecycle."""

    def __init__(self, task_manager: Optional[TaskManager] = None, memory=None):
        """
        Initialize the executor.

        Args:
            task_manager: TaskManager instance (defaults to global)
            memory: MemoryManager instance (defaults to global)
        """
        self.logger = get_logger(__name__)
        self.task_manager = (
            task_manager if task_manager is not None else TaskManager()
        )
        self.memory = memory if memory is not None else memory_manager
        # Track currently executing tasks to prevent duplicate execution
        self._executing_tasks: set[str] = set()

    async def execute_task(self, task: Task) -> bool:
        """
        Execute a single task.

        Args:
            task: The task to execute

        Returns:
            True if task completed successfully, False otherwise
        """
        # Prevent concurrent execution of the same task
        if task.id in self._executing_tasks:
            self.logger.warning(f"Task {task.id} is already being executed")
            return False

        self._executing_tasks.add(task.id)
        try:
            return await self._execute_task_internal(task)
        finally:
            self._executing_tasks.discard(task.id)

    async def _execute_task_internal(self, task: Task) -> bool:
        """Internal method to execute a task with retry logic."""
        self.logger.info(f"Executing task {task.id}: {task.title}")

        # Update task status to running
        await self.task_manager.update_task(
            task.id,
            status=TaskStatus.RUNNING,
            started_at=time.time(),
        )

        # Emit task started event
        publish(
            "task.execution_started",
            {
                "task_id": task.id,
                "title": task.title,
                "assigned_to": task.assigned_to,
            },
            source="Executor",
        )

        # Get the maximum number of retries from the task
        max_retries = task.max_retries
        retry_count = 0

        while retry_count <= max_retries:
            try:
                # Attempt to perform the task's action
                result = await self._perform_task_action(task)

                # If successful, mark task as completed
                await self.task_manager.complete_task(task.id, result)
                self.logger.info(
                    f"Task {task.id} completed successfully (attempt {retry_count + 1})"
                )

                # Emit task completed event
                publish(
                    "task.execution_completed",
                    {
                        "task_id": task.id,
                        "title": task.title,
                        "result": result,
                        "attempt": retry_count + 1,
                    },
                    source="Executor",
                )

                # Update memory with the successful execution
                await self._update_memory_on_success(task, result)
                return True

            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                self.logger.warning(
                    f"Task {task.id} failed on attempt {retry_count}/{max_retries + 1}: {error_msg}"
                )

                # If we have retries left, reset task to CREATED state for retry
                if retry_count <= max_retries:
                    await self.task_manager.update_task(
                        task.id,
                        status=TaskStatus.CREATED,  # Reset to await execution again
                        error=error_msg,
                    )
                    # Wait a bit before retry (exponential backoff optional)
                    await asyncio.sleep(min(2**retry_count, 10))
                else:
                    # Exhausted retries, mark as failed
                    await self.task_manager.fail_task(task.id, error_msg)
                    self.logger.error(
                        f"Task {task.id} failed permanently after {max_retries + 1} attempts: {error_msg}"
                    )

                    # Emit task failed event
                    publish(
                        "task.execution_failed",
                        {
                            "task_id": task.id,
                            "title": task.title,
                            "error": error_msg,
                            "attempts": retry_count,
                        },
                        source="Executor",
                    )

                    # Update memory with the failure
                    await self._update_memory_on_failure(task, error_msg)
                    return False

        return False  # Should not reach here

    async def _perform_task_action(self, task: Task) -> Any:
        """
        Perform the actual action for a task.
        This is where the real work happens. For now, we simulate work.

        Args:
            task: The task to execute

        Returns:
            The result of the task execution

        Raises:
            Exception: If the task execution fails
        """
        # Simulate work based on task type or description
        # In a real implementation, this would dispatch to skills or specific handlers

        # Extract any custom action from task metadata
        # For now, we'll just simulate based on whether the task title contains certain keywords
        title_lower = task.title.lower()
        description = task.description or ""

        # Simulate some work
        work_duration = 0.1  # Base work time in seconds
        if "backup" in title_lower:
            work_duration = 0.5
            # Simulate occasional backup failure
            if random.random() < 0.1:  # 10% chance of failure
                raise Exception("Backup failed: insufficient storage space")
        elif "analyze" in title_lower:
            work_duration = 0.3
        elif "delete" in title_lower:
            work_duration = 0.2
            # Simulate occasional deletion failure (e.g., file in use)
            if random.random() < 0.05:  # 5% chance of failure
                raise Exception("Deletion failed: file is in use")
        else:
            work_duration = 0.1

        # Simulate the work by sleeping
        await asyncio.sleep(work_duration)

        # For now, return a simple success result
        result = {
            "status": "completed",
            "message": f"Task '{task.title}' executed successfully",
            "details": {
                "duration": work_duration,
                "timestamp": time.time(),
            },
            "output": f"Completed action for task: {task.title}",
        }

        # Occasionally introduce a random failure for demonstration (5% chance for non-specialized tasks)
        if "backup" not in title_lower and "delete" not in title_lower:
            if random.random() < 0.05:
                raise Exception(f"Unexpected error during task execution: {task.title}")

        return result

    async def _update_memory_on_success(self, task: Task, result: Any) -> None:
        """Update memory after successful task execution."""
        # Store an episodic memory of the task completion
        episode_id = self.memory.store_episode(
            event_type="task_completed",
            data={
                "task_id": task.id,
                "title": task.title,
                "result": result,
            },
            importance=0.7,  # Successful task completion is moderately important
            tags=["task", "success", "completion"],
        )
        self.logger.debug(f"Stored task completion episode: {episode_id}")

        # If the task result indicates something important to remember, store in long-term memory
        # For example, if the task was to learn a fact or save a preference
        if isinstance(result, dict) and result.get("remember", False):
            self.memory.store(
                key=f"task_result_{task.id}",
                value=result.get("memory_content", result),
                long_term=True,
                importance=0.9,
                tags=["task_result", "important", "memory"],
            )

        # Also update short-term memory with recent task outcome for quick access
        self.memory.store(
            key=f"recent_task_{task.id}",
            value={
                "task_id": task.id,
                "title": task.title,
                "status": "success",
                "timestamp": time.time(),
            },
            importance=0.5,
            tags=["recent", "task"],
        )

    async def _update_memory_on_failure(self, task: Task, error_msg: str) -> None:
        """Update memory after failed task execution."""
        # Store an episodic memory of the task failure
        event_id = self.memory.store_episode(
            event_type="task_failed",
            data={
                "task_id": task.id,
                "title": task.title,
                "error": error_msg,
            },
            importance=0.6,  # Failures are somewhat important to remember
            tags=["task", "failure"],
        )
        self.logger.debug(f"Stored task failure episode: {event_id}")

        # Update short-term memory with recent failure
        self.memory.store(
            key=f"recent_task_{task.id}",
            value={
                "task_id": task.id,
                "title": task.title,
                "status": "failed",
                "error": error_msg,
                "timestamp": time.time(),
            },
            importance=0.5,
            tags=["recent", "task", "failure"],
        )

    async def execute_task_from_id(self, task_id: str) -> bool:
        """
        Execute a task by its ID (fetches the task from the task manager first).

        Args:
            task_id: The ID of the task to execute

        Returns:
            True if task completed successfully, False otherwise
        """
        task = await self.task_manager.get_task(task_id)
        if task is None:
            self.logger.error(f"Task {task_id} not found")
            return False
        return await self.execute_task(task)

    async def execute_next_task(self) -> bool:
        """
        Execute the next available task from the task queue.

        Returns:
            True if a task was executed successfully, False if no task available or execution failed
        """
        # Get the next task to execute
        task = await self.task_manager.get_next_task()
        if task is None:
            self.logger.debug("No tasks available for execution")
            return False

        return await self.execute_task(task)

    def get_executing_tasks(self) -> set[str]:
        """Get the set of task IDs currently being executed."""
        return self._executing_tasks.copy()