"""
Planning module for JARVIS-MK2.
Responsible for breaking down goals into actionable tasks.
"""

from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.events import publish
from tasks.task_manager import TaskManager, task_manager as global_task_manager

logger = get_logger(__name__)


class Planner:
    """Plans and decomposes goals into tasks."""

    def __init__(self, task_manager: Optional[TaskManager] = None):
        """Initialize the planner."""
        self.logger = get_logger(__name__)
        self.task_manager = task_manager if task_manager is not None else global_task_manager

    async def create_plan(self, goal: str) -> List[Dict[str, Any]]:
        """
        Create a plan to achieve a goal and add tasks to the task manager.

        Args:
            goal: The goal to achieve

        Returns:
            A list of task dictionaries (same as what was added to the task manager)
        """
        self.logger.info(f"Creating plan for goal: {goal}")

        # This is a simple rule-based planner for demonstration.
        # In a real system, this would use AI to break down the goal.
        task_defs = []  # List of task dictionaries to be created

        # Example: If the goal contains certain keywords, we break it down.
        # We'll create a few example tasks for now.
        if "organize" in goal.lower() and "file" in goal.lower():
            task_defs.append({
                "title": "Analyze files",
                "description": "Analyze the files to determine organization needs",
                "priority": "HIGH"
            })
            task_defs.append({
                "title": "Create organization plan",
                "description": "Create a plan for how to organize the files",
                "priority": "MEDIUM"
            })
            task_defs.append({
                "title": "Execute file organization",
                "description": "Rename and move files according to the plan",
                "priority": "HIGH"
            })
        else:
            # Default task
            task_defs.append({
                "title": f"Achieve goal: {goal}",
                "description": f"Work towards achieving the goal: {goal}",
                "priority": "MEDIUM"
            })

        # Create tasks in the task manager and collect their info
        created_tasks = []
        for task_def in task_defs:
            # Create the task in the task manager (this is async)
            task_obj = await self.task_manager.create_task(
                title=task_def["title"],
                description=task_def.get("description", ""),
                priority=self._priority_string_to_int(task_def["priority"])
            )
            # Convert the task object back to a dictionary for returning
            task_dict = {
                "id": task_obj.id,
                "title": task_obj.title,
                "description": task_obj.description,
                "priority": task_obj.priority,  # This is now an integer, but we can keep it or convert back
                "status": task_obj.status.value,
                "created_at": task_obj.created_at,
            }
            created_tasks.append(task_dict)

        # Publish planning event
        publish("planning.plan_created", {"plan": created_tasks}, source="Planner")

        return created_tasks

    def _priority_string_to_int(self, priority_str: str) -> int:
        """Convert priority string to integer for internal use."""
        priority_map = {
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1
        }
        return priority_map.get(priority_str.upper(), 2)  # Default to MEDIUM

    # For backward compatibility, we keep a synchronous method that does not add to task manager?
    # But we are replacing the existing method. However, note that the old method was synchronous and
    # did not interact with the task manager. We are changing the behavior.
    # Since we are in the middle of development and the only user is our test, we can change it.
    # If we need to keep the old behavior, we can rename this method and keep the old one.
    # Let's not overcomplicate: we are building the system as we go.

    # We'll keep the method as async and update the callers.

    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        import uuid
        return f"TASK-{uuid.uuid4().hex[:8].upper()}"

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()