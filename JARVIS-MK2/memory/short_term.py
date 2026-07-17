"""
Short-term memory for JARVIS-MK2.
Holds temporary information like current conversation and active tasks.
"""

from typing import Any, Dict, List, Optional
from collections import OrderedDict

from core.logger import get_logger

logger = get_logger(__name__)


class ShortTermMemory:
    """Short-term memory storage."""

    def __init__(self, max_size: int = 1000):
        """
        Initialize short-term memory.

        Args:
            max_size: Maximum number of items to store
        """
        self.logger = get_logger(__name__)
        self.max_size = max_size
        self._store: dict[str, Any] = {}
        self._access_order: list[str] = []  # LRU tracking

    def store(self, key: str, value: Any) -> None:
        """
        Store a value in short-term memory.

        Args:
            key: Storage key
            value: Value to store
        """
        if key in self._store:
            # Update existing key
            self._store[key] = value
            # Move to end of access order
            self._access_order.remove(key)
            self._access_order.append(key)
        else:
            # Add new key
            self._store[key] = value
            self._access_order.append(key)

            # Enforce size limit
            if len(self._store) > self.max_size:
                # Remove least recently used item
                lru_key = self._access_order.pop(0)
                del self._store[lru_key]
                self.logger.debug(f"Evicted LRU item from short-term memory: {lru_key}")

    def retrieve(self, key: str) -> Any:
        """
        Retrieve a value from short-term memory.

        Args:
            key: Retrieval key

        Returns:
            Value if found, None otherwise
        """
        if key in self._store:
            # Update access order (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._store[key]
        return None

    def forget(self, key: str) -> bool:
        """
        Forget a value from short-term memory.

        Args:
            key: Key to forget

        Returns:
            True if forgotten, False if not found
        """
        if key in self._store:
            del self._store[key]
            self._access_order.remove(key)
            self.logger.debug(f"Forgot from short-term memory: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all short-term memory."""
        self._store.clear()
        self._access_order.clear()
        self.logger.debug("Cleared short-term memory")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search short-term memory for items matching a query.

        Args:
            query: Search query (simple string matching for now)

        Returns:
            List of matching items with keys
        """
        results = []
        query_lower = query.lower()
        for key, value in self._store.items():
            if (
                query_lower in key.lower()
                or (isinstance(value, str) and query_lower in value.lower())
                or (
                    isinstance(value, dict)
                    and any(query_lower in str(v).lower() for v in value.values())
                )
            ):
                results.append(
                    {
                        "key": key,
                        "value": value,
                        "type": "short_term",
                    }
                )
        return results