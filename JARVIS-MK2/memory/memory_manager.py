"""
Memory manager for JARVIS-MK2.
Coordinates short-term and long-term memory systems.
"""

import time
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.events import publish

logger = get_logger(__name__)

# Import here to avoid circular dependencies
from .short_term import ShortTermMemory
from .long_term import LongTermMemory


class MemoryManager:
    """Manages memory systems for JARVIS-MK2."""

    def __init__(self):
        """Initialize the memory manager."""
        self.logger = get_logger(__name__)
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        # Episodic memory for session events
        from .episodic import EpisodicMemory
        self.episodic = EpisodicMemory()

    def store(
        self,
        key: str,
        value: Any,
        long_term: bool = False,
        importance: float = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Store a value in memory.

        Args:
            key: Storage key
            value: Value to store
            long_term: Whether to store in long-term memory
            importance: Importance score (0.0 to 1.0). If None, defaults to 0.5 for short-term, 0.7 for long-term?
            tags: Optional list of tags for categorization
        """
        # Set default importance if not provided
        if importance is None:
            importance = 0.5 if not long_term else 0.7

        if tags is None:
            tags = []

        if long_term:
            self.long_term.store(key, value, importance=importance, tags=tags)
            self.logger.debug(f"Stored in long-term memory: {key}")
        else:
            self.short_term.store(key, value, importance=importance, tags=tags)
            self.logger.debug(f"Stored in short-term memory: {key}")

        # Store in both if it's important and not already in long-term?
        # We'll let the caller decide by setting long_term=True if they want both.

        # Publish memory storage event
        publish(
            "memory.stored",
            {
                "key": key,
                "long_term": long_term,
                "importance": importance,
                "tags": tags,
            },
            source="MemoryManager",
        )

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

    def get_memory(self, key: str) -> Optional[dict]:
        """
        Get the memory item (value and metadata) by key.
        Checks short-term first, then long-term.

        Args:
            key: Retrieval key

        Returns:
            Dict with keys 'value', 'importance', 'timestamp', 'tags', 'type' (either 'short_term' or 'long_term')
            or None if not found.
        """
        # Check short-term
        meta = self.short_term.get_metadata(key)
        if meta is not None:
            meta['type'] = 'short_term'
            return meta

        # Check long-term
        meta = self.long_term.get_metadata(key)
        if meta is not None:
            meta['type'] = 'long_term'
            return meta

        return None

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
        self.episodic.clear()
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
        results.extend(self.episodic.search(query))
        return results

    def store_episode(
        self,
        event_type: str,
        data: Any,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Store an episodic memory (event that happened during a session).

        Args:
            event_type: Type of event (e.g., 'task_completed', 'user_command')
            data: The event data
            importance: Importance score
            tags: Optional tags

        Returns:
            The episode ID
        """
        episode_id = self.episodic.store(event_type, data, importance=importance, tags=tags)
        return episode_id

    def get_recent_episodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent episodic memories.

        Args:
            limit: Maximum number to return

        Returns:
            List of episodic memories, most recent first
        """
        return self.episodic.get_recent(limit)


# Global memory manager instance
memory_manager = MemoryManager()