"""
Critic module for JARVIS-MK2.
Reviews decisions and suggests improvements.
"""

from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.events import publish

logger = get_logger(__name__)


class Critic:
    """Reviews decisions and provides feedback."""

    def __init__(self):
        """Initialize the critic."""
        self.logger = get_logger(__name__)

    def review_decision(self, decision: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Review a decision and provide feedback.

        Args:
            decision: Decision dictionary to review
            context: Additional context for the review

        Returns:
            Review results with approval status, comments, and suggestions
        """
        self.logger.info("Reviewing decision")

        # This is a simple rule-based critic for demonstration.
        review = {
            "decision_id": decision.get("id", "unknown"),
            "timestamp": self._get_timestamp(),
            "approved": True,
            "confidence": 0.8,
            "issues": [],
            "suggestions": [],
            "comments": []
        }

        # Check for empty decision
        if not decision:
            review["approved"] = False
            review["confidence"] = 0.9
            review["issues"].append("Empty decision")
            review["suggestions"].append("Provide a valid decision")
            return review

        # Example check: if a decision involves deleting files without backup, flag it
        # We'll look for keys that might indicate an action
        action = decision.get("action", "").lower()
        parameters = decision.get("parameters", {})
        param_str = str(parameters).lower()

        if "delete" in action or "delete" in param_str:
            if "backup" not in action and "backup" not in param_str:
                issue = "Decision involves deletion without mention of backup"
                review["issues"].append(issue)
                review["suggestions"].append("Add a backup step before deletion")
                # For now, we don't disapprove, just note the issue

        # Check for missing required fields
        if "action" not in decision:
            issue = "Decision is missing an action"
            self.logger.warning(issue)
            review["issues"].append(issue)
            review["suggestions"].append("Specify an action to take")

        # If there are any issues, we might not approve
        if review["issues"]:
            review["approved"] = False
            # Adjust confidence based on number of issues
            review["confidence"] = max(0.1, 0.8 - (len(review["issues"]) * 0.1))

        # Add some general comments
        if "priority" not in decision:
            comment = "Consider adding a priority to the decision"
            self.logger.debug(comment)
            review["comments"].append(comment)

        # Publish review event
        publish("critic.review_completed", {"review": review}, source="Critic")

        return review

    def suggest_improvements(
        self, decision: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Suggest improvements for a decision.

        Args:
            decision: The decision to improve
            context: Additional context

        Returns:
            List of improvement suggestions
        """
        # We can reuse the review process to get suggestions
        review = self.review_decision(decision, context)
        return review["suggestions"]

    def review_plan(self, plan: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Review a plan and provide feedback.

        Args:
            plan: List of task dictionaries to review
            context: Additional context for the review

        Returns:
            Review results with approval status, comments, and suggestions
        """
        self.logger.info(f"Reviewing plan with {len(plan)} tasks")

        # This is a simple rule-based critic for demonstration.
        review = {
            "plan_id": self._generate_plan_id(plan),
            "timestamp": self._get_timestamp(),
            "approved": True,
            "confidence": 0.8,
            "issues": [],
            "suggestions": [],
            "comments": []
        }

        # Check for empty plan
        if not plan:
            review["approved"] = False
            review["confidence"] = 0.9
            review["issues"].append("Empty plan")
            review["suggestions"].append("Provide at least one task in the plan")
            return review

        # Check each task for potential issues
        for i, task in enumerate(plan):
            task_id = task.get("id", f"unknown_task_{i}")
            title = task.get("title", "").lower()
            description = task.get("description", "").lower()

            # Example check: if a task mentions deleting files without backup, flag it
            if "delete" in title or "delete" in description:
                if "backup" not in title and "backup" not in description:
                    issue = f"Task '{task_id}' involves deletion without mention of backup"
                    self.logger.debug(issue)
                    review["issues"].append(issue)
                    review["suggestions"].append(f"Add a backup step before deletion in task {task_id}")
                    # Depending on severity, we might set approved to False
                    # For now, we'll just note it and let the user decide.

            # Check for unclear tasks
            if len(title) < 3:
                issue = f"Task '{task_id}' has a very short title: '{title}'"
                self.logger.debug(issue)
                review["issues"].append(issue)
                review["suggestions"].append(f"Make the title more descriptive for task {task_id}")

            # Check for missing priority or status (though these should be set by the planner)
            if "priority" not in task:
                issue = f"Task '{task_id}' is missing priority"
                self.logger.debug(issue)
                review["issues"].append(issue)
                review["suggestions"].append(f"Assign a priority (HIGH, MEDIUM, LOW) to task {task_id}")

            if "status" not in task:
                issue = f"Task '{task_id}' is missing status"
                self.logger.debug(issue)
                review["issues"].append(issue)
                review["suggestions"].append(f"Set a status (e.g., CREATED) for task {task_id}")

        # If there are any issues that are considered critical, we might disapprove the plan.
        # For now, we'll consider any issue as making the plan not approved, but we'll leave it to the user.
        # Let's say: if there are any issues, we set approved to False but still provide suggestions.
        if review["issues"]:
            self.logger.debug("Plan has issues, marking as not approved")
            review["approved"] = False
            # We might adjust confidence based on number of issues
            review["confidence"] = max(0.1, 0.8 - (len(review["issues"]) * 0.1))

        # Add some general comments
        if len(plan) > 5:
            comment = f"Plan has {len(plan)} tasks, which is quite large. Consider breaking into phases."
            self.logger.debug(comment)
            review["comments"].append(comment)

        # Publish review event
        publish("critic.review_completed", {"review": review}, source="Critic")

        return review

    def _generate_plan_id(self, plan: List[Dict[str, Any]]) -> str:
        """Generate a unique ID for the plan based on its contents."""
        import hashlib
        import json
        # Sort the plan by task id to have a consistent representation
        try:
            sorted_plan = sorted(plan, key=lambda x: x.get("id", ""))
        except Exception:
            sorted_plan = plan
        plan_str = json.dumps(sorted_plan, sort_keys=True)
        return f"PLAN-{hashlib.md5(plan_str.encode()).hexdigest()[:8].upper()}"

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()