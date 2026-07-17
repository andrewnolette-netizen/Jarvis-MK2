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
            options: List of options to choose from. Each option should have:
                     - priority (int or string that can be mapped to int)
                     - risk (optional, int or string, lower is better)
                     - dependencies (optional, list of task IDs, fewer is better)
            context: Additional context for decision making

        Returns:
            Selected option with metadata
        """
        self.logger.info(f"Making decision from {len(options)} options")

        if not options:
            return {"error": "No options provided"}

        # We'll convert each option to a score.
        # We'll define a simple scoring function:
        #   score = priority_weight * priority - risk_weight * risk - dependencies_weight * len(dependencies)
        # Weights can be adjusted.

        priority_weight = 1.0
        risk_weight = 0.5
        dependencies_weight = 0.3

        scored_options = []
        for option in options:
            # Get priority, default to 0
            priority = option.get("priority", 0)
            if isinstance(priority, str):
                # Try to convert string priority to int
                priority_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
                priority = priority_map.get(priority.upper(), 0)

            # Get risk, default to 0 (if not provided, assume no risk)
            risk = option.get("risk", 0)
            if isinstance(risk, str):
                risk_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
                risk = risk_map.get(risk.upper(), 0)

            # Get dependencies, default to empty list
            dependencies = option.get("dependencies", [])
            if not isinstance(dependencies, list):
                dependencies = []

            # Calculate score
            score = (priority_weight * priority) - (risk_weight * risk) - (dependencies_weight * len(dependencies))

            scored_options.append({
                "option": option,
                "score": score,
                "priority": priority,
                "risk": risk,
                "dependency_count": len(dependencies)
            })

        # Sort by score descending
        scored_options.sort(key=lambda x: x["score"], reverse=True)

        # Select the top option
        best = scored_options[0]
        selected_option = best["option"].copy()
        selected_option["selected_at"] = self._get_timestamp()
        selected_option["selection_reason"] = f"Highest score: {best['score']}"

        # Publish decision event
        publish("decision.made", {"decision": selected_option}, source="DecisionEngine")

        return selected_option

    def evaluate_options(
        self, options: List[Dict[str, Any]], criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate options against criteria.

        Args:
            options: Options to evaluate
            criteria: Criteria to evaluate against (e.g., weights for scoring)

        Returns:
            Options with scores added
        """
        # For simplicity, we'll just return the options with a score based on the criteria.
        # But note: the criteria might be different from the weights we used in make_decision.
        # We'll implement a simple version for now.

        evaluated = []
        for option in options:
            scored_option = option.copy()
            score = 0
            # Simple scoring - in reality this would be more complex
            for key, weight in criteria.items():
                if key in option:
                    # Try to convert to number if it's a string
                    value = option[key]
                    if isinstance(value, str):
                        # Try to map common strings
                        if key == "priority":
                            value_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
                            value = value_map.get(value.upper(), 0)
                        elif key == "risk":
                            value_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
                            value = value_map.get(value.upper(), 0)
                        else:
                            # Try to convert to int
                            try:
                                value = int(value)
                            except ValueError:
                                value = 0
                    score += value * weight
            scored_option["score"] = score
            evaluated.append(scored_option)

        return evaluated

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()