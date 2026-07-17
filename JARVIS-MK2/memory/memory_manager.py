"""
Memory manager for JARVIS-MK2.
Coordinates short-term and long-term memory systems.
"""

from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.events import publish

logger = get_logger(__name__)


class MemoryManager:
    """Manages memory systems for JARVIS-MK2."""

    def __init__(self):
        """Initialize the memory manager."""
        self.logger = get_logger(__name__)
        # Import here to avoid circular dependencies
        from .short_term import ShortTermMemory
        from .long_term import LongTermMemory

        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

    def store(self, key: str, value: Any, long_term: bool = False) -> None:
        """
        Store a value in memory.

        Args:
            key: Storage key
            value: Value to store
            long_term: Whether to store in long-term memory
        """
        if long_term:
            self.long_term.store(key, value)
            self.logger.debug(f"Stored in long-term memory: {key}")
        else:
            self.short_term.store(key, value)
            self.logger.debug(f"Stored in short-term memory: {key}")

        # Store in both if it's important
        if hasattr(value, "__dict__") and getattr(value, "important", False):
            self.long_term.store(key, value)
            self.logger.debug(f"Also stored in long-term memory (marked important): {key}")

    def retrieve(self, key: str) -> Any:
        """
        Retrieve a value from memory.

        Args:
            key: Retrieval key

        Returns:
            Value if found, None otherwise
        """
        # Check short-term first
        value = self.short_term.retrieve(key)
        if value is not None:
            return value

        # Then check long-term
        return self.long_term.retrieve(key)

    def forget(self, key: str) -> bool:
        """
        Forget a value from memory.

        Args:
            key: Key to forget

        Returns:
            True if forgotten from either memory, False if not found
        """
        forgotten_st = self.short_term.forget(key)
        forgotten_lt = self.long_term.forget(key)
        return forgotten_st or forgotten_lt

    def clear(self) -> None:
        """Clear all memory."""
        self.short_term.clear()
        self.long_term.clear()
        self.logger.info("Cleared all memory")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search memory for items matching a query.

        Args:
            query: Search query

        Returns:
            List of matching items with metadata
        """
        results = []
        results.extend(self.short_term.search(query))
        results.extend(self.long_term.search(query))
        return results


# Global memory manager instance
memory_manager = MemoryManager()