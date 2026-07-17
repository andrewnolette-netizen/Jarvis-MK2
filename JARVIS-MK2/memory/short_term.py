"""
Short-term memory for JARVIS-MK2.
Holds temporary information like current conversation and active tasks.
"""

import time
from typing import Any, Dict, List, Optional

from core.logger import get_logger

logger = get_logger(__name__)


class ShortTermMemory:
    """Short-term memory storage with metadata support."""

    def __init__(self, max_size: int = 1000):
        """
        Initialize short-term memory.

        Args:
            max_size: Maximum number of items to store
        """
        self.logger = get_logger(__name__)
        self.max_size = max_size
        # Store: key -> {'value': any, 'importance': float, 'timestamp': float, 'tags': list}
        self._store: dict[str, dict] = {}
        self._access_order: list[str] = []  # LRU tracking

    def store(
        self,
        key: str,
        value: Any,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Store a value in short-term memory with metadata.

        Args:
            key: Storage key
            value: Value to store
            importance: Importance score (0.0 to 1.0, default 0.5)
            tags: Optional list of tags for categorization
        """
        if tags is None:
            tags = []
        now = time.time()
        item = {
            'value': value,
            'importance': max(0.0, min(1.0, importance)),  # clamp to [0,1]
            'timestamp': now,
            'tags': tags,
        }

        if key in self._store:
            # Update existing key
            self._store[key] = item
            # Move to end of access order
            self._access_order.remove(key)
            self._access_order.append(key)
        else:
            # Add new key
            self._store[key] = item
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
            return self._store[key]['value']
        return None

    def get_metadata(self, key: str) -> Optional[dict]:
        """
        Get metadata for a key.

        Args:
            key: Key to get metadata for

        Returns:
            Metadata dict if found, None otherwise
        """
        if key in self._store:
            # Return a copy to prevent accidental mutation
            return self._store[key].copy()
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
            List of matching items with keys and metadata
        """
        results = []
        query_lower = query.lower()
        for key, item in self._store.items():
            match = False
            # Check key
            if query_lower in key.lower():
                match = True
            # Check value if it's a string
            elif isinstance(item['value'], str) and query_lower in item['value'].lower():
                match = True
            # Check tags
            elif any(query_lower in tag.lower() for tag in item['tags']):
                match = True
            # Check if value is dict and search its string values
            elif isinstance(item['value'], dict):
                if any(
                    query_lower in str(v).lower()
                    for v in item['value'].values()
                    if isinstance(v, str)
                ):
                    match = True

            if match:
                results.append(
                    {
                        'key': key,
                        'value': item['value'],
                        'importance': item['importance'],
                        'timestamp': item['timestamp'],
                        'tags': item['tags'],
                        'type': 'short_term',
                    }
                )
        return results