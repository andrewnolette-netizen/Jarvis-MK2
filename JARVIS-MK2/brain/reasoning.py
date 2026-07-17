"""
Reasoning module for JARVIS-MK2.
Handles logical reasoning and inference.
"""

from typing import Any, Dict, List, Optional, Union

from core.logger import get_logger
from core.events import publish

logger = get_logger(__name__)


class Reasoner:
    """Performs logical reasoning and inference."""

    def __init__(self):
        """Initialize the reasoner."""
        self.logger = get_logger(__name__)
        self.facts: dict[str, Any] = {}
        self.rules: list[dict] = []

    def add_fact(self, key: str, value: Any) -> None:
        """
        Add a fact to the knowledge base.

        Args:
            key: Fact identifier
            value: Fact value
        """
        self.facts[key] = value
        self.logger.debug(f"Added fact: {key} = {value}")

    def add_rule(self, condition: callable, conclusion: Any) -> None:
        """
        Add a rule to the knowledge base.

        Args:
            condition: Function that takes facts and returns bool
            conclusion: What to conclude when condition is true
        """
        self.rules.append({"condition": condition, "conclusion": conclusion})
        self.logger.debug("Added rule")

    def infer(self) -> List[Dict[str, Any]]:
        """
        Run inference on the current knowledge base.

        Returns:
            List of inferences made
        """
        inferences = []
        for rule in self.rules:
            try:
                if rule["condition"](self.facts):
                    inference = {
                        "condition_met": True,
                        "conclusion": rule["conclusion"],
                        "timestamp": self._get_timestamp(),
                    }
                    inferences.append(inference)
                    self.logger.debug(f"Made inference: {rule['conclusion']}")
            except Exception as e:
                self.logger.error(f"Error applying rule: {e}")

        return inferences

    def query(self, key: str) -> Any:
        """
        Query a fact from the knowledge base.

        Args:
            key: Fact identifier

        Returns:
            Fact value or None if not found
        """
        return self.facts.get(key)

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()