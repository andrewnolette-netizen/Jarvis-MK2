"""
Long-term memory for JARVIS-MK2.
Stores persistent information like preferences and important facts.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.config import config

logger = get_logger(__name__)


class LongTermMemory:
    """Long-term memory storage with optional persistence."""

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
        self._store: dict[str, Any] = {}

        # Ensure storage directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data if available
        self._load()

    def _load(self) -> None:
        """Load data from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    self._store = json.load(f)
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
            with open(self.storage_path, "w") as f:
                json.dump(self._store, f, indent=2, default=str)
            self.logger.debug(f"Saved long-term memory to {self.storage_path}")
        except Exception as e:
            self.logger.error(f"Error saving long-term memory: {e}")

    def store(self, key: str, value: Any) -> None:
        """
        Store a value in long-term memory.

        Args:
            key: Storage key
            value: Value to store (must be JSON serializable)
        """
        self._store[key] = value
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
        return self._store.get(key)

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
                        "type": "long_term",
                    }
                )
        return results

    def get_all(self) -> Dict[str, Any]:
        """
        Get all stored items.

        Returns:
            Dictionary of all key-value pairs
        """
        return self._store.copy()