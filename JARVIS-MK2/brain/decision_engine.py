"""
Decision engine for JARVIS-MK2.
Responsible for choosing actions and evaluating options.
"""

from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.events import publish

logger = get_logger(__name__)


class DecisionEngine:
    """Makes decisions based on available information."""

    def __init__(self):
        """Initialize the decision engine."""
        self.logger = get_logger(__name__)

    def make_decision(
        self, options: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a decision from a set of options.

        Args:
            options: List of options to choose from
            context: Additional context for decision making

        Returns:
            Selected option with metadata
        """
        self.logger.info(f"Making decision from {len(options)} options")

        # Simple implementation: choose the option with highest priority/score
        # In a real system, this would use more sophisticated reasoning
        if not options:
            return {"error": "No options provided"}

        # Sort by priority or score if available
        sorted_options = sorted(
            options,
            key=lambda x: x.get("priority", x.get("score", 0)),
            reverse=True,
        )

        selected = sorted_options[0].copy()
        selected["selected_at"] = self._get_timestamp()
        selected["selection_reason"] = "Highest priority/score"

        # Publish decision event
        publish("decision.made", {"decision": selected}, source="DecisionEngine")

        return selected

    def evaluate_options(
        self, options: List[Dict[str, Any]], criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate options against criteria.

        Args:
            options: Options to evaluate
            criteria: Criteria to evaluate against

        Returns:
            Options with scores added
        """
        evaluated = []
        for option in options:
            scored_option = option.copy()
            score = 0
            # Simple scoring - in reality this would be more complex
            for key, weight in criteria.items():
                if key in option:
                    score += option[key] * weight
            scored_option["score"] = score
            evaluated.append(scored_option)

        return evaluated

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()