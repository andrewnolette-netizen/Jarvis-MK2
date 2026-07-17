"""
Long-term memory for JARVIS-MK2.
Stores persistent information like preferences and important facts.
"""

import json
import time
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.config import config

logger = get_logger(__name__)


class LongTermMemory:
    """Long-term memory storage with optional persistence and metadata."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize long-term memory.

        Args:
            storage_path: Path to storage file (if None, uses config)
        """
        self.logger = get_logger(__name__)
        if storage_path is None:
            storage_path = config.get(
                "memory.long_term.path", "data/long_term_memory.json"
            )
        self.storage_path = Path(storage_path)
        # Store: key -> {'value': any, 'importance': float, 'timestamp': float, 'tags': list}
        self._store: dict[str, dict] = {}

        # Ensure storage directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data if available
        self._load()

    def _load(self) -> None:
        """Load data from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    raw_data = json.load(f)
                # Convert stored items to our format if they are not already
                # For backward compatibility, if the value is not a dict with our expected keys,
                # we wrap it.
                self._store = {}
                for key, value in raw_data.items():
                    if isinstance(value, dict) and 'value' in value:
                        # Already in our format
                        self._store[key] = value
                    else:
                        # Old format: just the value
                        self._store[key] = {
                            'value': value,
                            'importance': 0.5,
                            'timestamp': time.time(),
                            'tags': [],
                        }
                self.logger.info(f"Loaded long-term memory from {self.storage_path}")
            except Exception as e:
                self.logger.error(f"Error loading long-term memory: {e}")
                self._store = {}
        else:
            self.logger.info(
                f"No existing long-term memory found at {self.storage_path}"
            )

    def _save(self) -> None:
        """Save data to storage file."""
        try:
            # Prepare data for JSON serialization: we store the entire item dict
            with open(self.storage_path, "w") as f:
                json.dump(self._store, f, indent=2, default=str)
            self.logger.debug(f"Saved long-term memory to {self.storage_path}")
        except Exception as e:
            self.logger.error(f"Error saving long-term memory: {e}")

    def store(
        self,
        key: str,
        value: Any,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Store a value in long-term memory with metadata.

        Args:
            key: Storage key
            value: Value to store (must be JSON serializable)
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
        self._store[key] = item
        self._save()
        self.logger.debug(f"Stored in long-term memory: {key}")

    def retrieve(self, key: str) -> Any:
        """
        Retrieve a value from long-term memory.

        Args:
            key: Retrieval key

        Returns:
            Value if found, None otherwise
        """
        if key in self._store:
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
        Forget a value from long-term memory.

        Args:
            key: Key to forget

        Returns:
            True if forgotten, False if not found
        """
        if key in self._store:
            del self._store[key]
            self._save()
            self.logger.debug(f"Forgot from long-term memory: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all long-term memory."""
        self._store.clear()
        self._save()
        self.logger.info("Cleared long-term memory")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search long-term memory for items matching a query.

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
                        'type': 'long_term',
                    }
                )
        return results

    def get_all(self) -> Dict[str, Any]:
        """
        Get all stored items.

        Returns:
            Dictionary of all key-value pairs (just the values, not metadata)
        """
        return {key: item['value'] for key, item in self._store.items()}

    def get_all_with_metadata(self) -> Dict[str, dict]:
        """
        Get all stored items with metadata.

        Returns:
            Dictionary of all key-value pairs with metadata
        """
        return self._store.copy()