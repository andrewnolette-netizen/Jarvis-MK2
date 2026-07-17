"""
Task manager for JARVIS-MK2.
Manages task creation, assignment, and tracking.
"""

import asyncio
import heapq
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.events import publish

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass
class Task:
    """Represents a task in the system."""
    id: str
    title: str
    description: str
    priority: int = 1
    status: TaskStatus = TaskStatus.CREATED
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    assigned_to: Optional[str] = None
    result: Any = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "dependencies": self.dependencies,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "assigned_to": self.assigned_to,
            "result": self.result,
            "error": self.error,
        }


class TaskManager:
    """Manages tasks in the system."""

    def __init__(self):
        """Initialize the task manager."""
        self.logger = get_logger(__name__)
        self._tasks: dict[str, Task] = {}
        # Priority queue for task scheduling (negative priority for max-heap behavior)
        self._task_queue: list[tuple[int, str]] = []  # (-priority, task_id)
        self._lock = asyncio.Lock()

    async def create_task(
        self,
        title: str,
        description: str,
        priority: int = 1,
        dependencies: Optional[List[str]] = None,
        assigned_to: Optional[str] = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            title: Task title
            description: Task description
            priority: Task priority (higher = more important)
            dependencies: List of task IDs this task depends on
            assigned_to: Module or agent assigned to this task

        Returns:
            Created task
        """
        import uuid

        task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            assigned_to=assigned_to,
        )

        async with self._lock:
            self._tasks[task_id] = task
            # Add to priority queue
            heapq.heappush(self._task_queue, (-priority, task_id))

        self.logger.info(f"Created task {task_id}: {title}")
        publish("task.created", {"task": task.to_dict()}, source="TaskManager")

        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        return self._tasks.get(task_id)

    async def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """
        Update a task's attributes.

        Args:
            task_id: Task ID
            **kwargs: Attributes to update

        Returns:
            Updated task if found, None otherwise
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
                else:
                    self.logger.warning(f"Task has no attribute '{key}'")

            # If status changed, update timestamps
            if "status" in kwargs:
                if kwargs["status"] == TaskStatus.RUNNING and task.started_at is None:
                    task.started_at = asyncio.get_event_loop().time()
                elif kwargs["status"] in (TaskStatus.SUCCESS, TaskStatus.FAILED):
                    task.completed_at = asyncio.get_event_loop().time()

            # Re-add to queue if priority changed
            if "priority" in kwargs:
                # Remove old entry (inefficient but simple)
                self._task_queue = [
                    (p, tid) for (p, tid) in self._task_queue if tid != task_id
                ]
                heapq.heapify(self._task_queue)
                heapq.heappush(self._task_queue, (-task.priority, task_id))

        publish("task.updated", {"task": task.to_dict()}, source="TaskManager")
        return task

    async def complete_task(
        self, task_id: str, result: Any = None
    ) -> Optional[Task]:
        """
        Mark a task as completed successfully.

        Args:
            task_id: Task ID
            result: Task result

        Returns:
            Updated task if found, None otherwise
        """
        return await self.update_task(
            task_id,
            status=TaskStatus.SUCCESS,
            result=result,
        )

    async def fail_task(
        self, task_id: str, error: str
    ) -> Optional[Task]:
        """
        Mark a task as failed.

        Args:
            task_id: Task ID
            error: Error message

        Returns:
            Updated task if found, None otherwise
        """
        task = await self.get_task(task_id)
        if not task:
            return None

        # Check if we should retry
        if task.retry_count < task.max_retries:
            await self.update_task(
                task_id,
                status=TaskStatus.CREATED,  # Reset to CREATED for retry
                retry_count=task.retry_count + 1,
                error=error,
            )
            self.logger.info(
                f"Task {task_id} failed, retrying ({task.retry_count + 1}/{task.max_retries})"
            )
        else:
            await self.update_task(
                task_id,
                status=TaskStatus.FAILED,
                error=error,
            )
            self.logger.error(f"Task {task_id} failed permanently: {error}")

        return await self.get_task(task_id)

    async def block_task(self, task_id: str, reason: str) -> Optional[Task]:
        """
        Block a task.

        Args:
            task_id: Task ID
            reason: Reason for blocking

        Returns:
            Updated task if found, None otherwise
        """
        return await self.update_task(
            task_id, status=TaskStatus.BLOCKED, error=f"Blocked: {reason}"
        )

    async def unblock_task(self, task_id: str) -> Optional[Task]:
        """
        Unblock a task (returns to CREATED state).

        Args:
            task_id: Task ID

        Returns:
            Updated task if found, None otherwise
        """
        task = await self.get_task(task_id)
        if task and task.status == TaskStatus.BLOCKED:
            return await self.update_task(task_id, status=TaskStatus.CREATED, error=None)
        return task

    async def get_next_task(self) -> Optional[Task]:
        """
        Get the next task to run based on priority and dependencies.

        Returns:
            Next task to run, or None if no tasks ready
        """
        async with self._lock:
            # We'll implement a simple priority-based scheduler
            # In reality, we'd need to check dependencies
            while self._task_queue:
                neg_priority, task_id = heapq.heappop(self._task_queue)
                task = self._tasks.get(task_id)
                if not task:
                    continue  # Task was removed

                # Check if dependencies are satisfied
                if await self._dependencies_satisfied(task):
                    # Task is ready to run
                    return task
                else:
                    # Dependencies not met, put it back and try next
                    heapq.heappush(self._task_queue, (neg_priority, task_id))
                    # To avoid infinite loop, we'll break after one full cycle
                    # In a real implementation, we'd have a more sophisticated approach
                    break

        return None

    async def _dependencies_satisfied(self, task: Task) -> bool:
        """
        Check if all dependencies for a task are satisfied.

        Args:
            task: Task to check

        Returns:
            True if dependencies are satisfied, False otherwise
        """
        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if not dep_task:
                self.logger.warning(
                    f"Dependency {dep_id} not found for task {task.id}"
                )
                return False
            if dep_task.status != TaskStatus.SUCCESS:
                return False
        return True

    def get_task_count(self) -> int:
        """Get the total number of tasks."""
        return len(self._tasks)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status."""
        return [task for task in self._tasks.values() if task.status == status]


# Global task manager instance
task_manager = TaskManager()