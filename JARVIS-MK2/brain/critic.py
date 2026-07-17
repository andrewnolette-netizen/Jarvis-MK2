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

    def review_decision(
        self, decision: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Review a decision and provide feedback.

        Args:
            decision: The decision to review
            context: Additional context for the review

        Returns:
            Review results with suggestions
        """
        self.logger.info("Reviewing decision")

        # This is a placeholder implementation
        review = {
            "decision_id": decision.get("id", "unknown"),
            "timestamp": self._get_timestamp(),
            "approved": True,
            "confidence": 0.8,
            "issues": [],
            "suggestions": [],
        }

        # Simple validation
        if not decision:
            review["approved"] = False
            review["issues"].append("Empty decision")
        elif "error" in decision:
            review["approved"] = False
            review["issues"].append(f"Decision contains error: {decision['error']}")

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
        suggestions = []

        # Placeholder logic
        if "priority" not in decision:
            suggestions.append("Consider adding priority to the decision")

        if not decision.get("selected_at"):
            suggestions.append("Decision lacks timestamp")

        return suggestions

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()