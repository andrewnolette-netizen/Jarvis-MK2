"""
Episodic memory for JARVIS-MK2.
Stores events that happened during each session.
"""

import time
import uuid
from typing import Any, Dict, List, Optional

from core.logger import get_logger

logger = get_logger(__name__)


class EpisodicMemory:
    """Episodic memory storage."""

    def __init__(self, max_size: int = 10000):
        """
        Initialize episodic memory.

        Args:
            max_size: Maximum number of episodes to store
        """
        self.logger = get_logger(__name__)
        self.max_size = max_size
        # Store: episode_id -> {
        #   'event_type': str,
        #   'data': any,
        #   'importance': float,
        #   'timestamp': float,
        #   'tags': list,
        #   'session_id': str
        # }
        self._store: dict[str, dict] = {}
        self._access_order: list[str] = []  # LRU tracking
        # Generate a session ID for this instance
        self.session_id = f"session-{uuid.uuid4().hex[:8]}"

    def store(
        self,
        event_type: str,
        data: Any,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Store an episodic memory.

        Args:
            event_type: Type of event (e.g., 'task_completed', 'user_command')
            data: The event data
            importance: Importance score (0.0 to 1.0, default 0.5)
            tags: Optional list of tags for categorization

        Returns:
            The generated episode ID
        """
        if tags is None:
            tags = []
        now = time.time()
        episode_id = f"epi-{uuid.uuid4().hex[:8]}"
        episode = {
            'event_type': event_type,
            'data': data,
            'importance': max(0.0, min(1.0, importance)),
            'timestamp': now,
            'tags': tags,
            'session_id': self.session_id,
        }

        self._store[episode_id] = episode
        self._access_order.append(episode_id)

        # Enforce size limit
        if len(self._store) > self.max_size:
            # Remove least recently used episode
            lru_id = self._access_order.pop(0)
            del self._store[lru_id]
            self.logger.debug(f"Evicted LRU episode from episodic memory: {lru_id}")

        self.logger.debug(
            f"Stored episodic memory: {episode_id} (type: {event_type}, importance: {episode['importance']})"
        )
        return episode_id

    def retrieve(self, episode_id: str) -> Optional[dict]:
        """
        Retrieve an episodic memory by ID.

        Args:
            episode_id: The episode ID

        Returns:
            The episode dict if found, None otherwise
        """
        if episode_id in self._store:
            # Update access order (most recently used)
            self._access_order.remove(episode_id)
            self._access_order.append(episode_id)
            # Return a copy to prevent accidental mutation
            return self._store[episode_id].copy()
        return None

    def get_metadata(self, episode_id: str) -> Optional[dict]:
        """
        Get metadata for an episode (same as retrieve for episodic memory).

        Args:
            episode_id: The episode ID

        Returns:
            The episode dict if found, None otherwise
        """
        return self.retrieve(episode_id)

    def forget(self, episode_id: str) -> bool:
        """
        Forget an episodic memory.

        Args:
            episode_id: The episode ID to forget

        Returns:
            True if forgotten, False if not found
        """
        if episode_id in self._store:
            del self._store[episode_id]
            self._access_order.remove(episode_id)
            self.logger.debug(f"Forgot episodic memory: {episode_id}")
            return True
        return False

    def clear(self) -> None:
        """Clear all episodic memory."""
        self._store.clear()
        self._access_order.clear()
        self.logger.debug("Cleared episodic memory")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search episodic memory for items matching a query.

        Args:
            query: Search query (simple string matching for now)

        Returns:
            List of matching episodes with metadata
        """
        results = []
        query_lower = query.lower()
        for episode_id, episode in self._store.items():
            match = False
            # Check event_type
            if query_lower in episode['event_type'].lower():
                match = True
            # Check data if it's a string
            elif isinstance(episode['data'], str) and query_lower in episode['data'].lower():
                match = True
            # Check tags
            elif any(query_lower in tag.lower() for tag in episode['tags']):
                match = True
            # Check if data is dict and search its string values
            elif isinstance(episode['data'], dict):
                if any(
                    query_lower in str(v).lower()
                    for v in episode['data'].values()
                    if isinstance(v, str)
                ):
                    match = True

            if match:
                results.append(
                    {
                        'episode_id': episode_id,
                        'event_type': episode['event_type'],
                        'data': episode['data'],
                        'importance': episode['importance'],
                        'timestamp': episode['timestamp'],
                        'tags': episode['tags'],
                        'session_id': episode['session_id'],
                        'type': 'episodic',
                    }
                )
        return results

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent episodic memories, most recent first.

        Args:
            limit: Maximum number to return

        Returns:
            List of episodic memories, most recent first
        """
        # We'll sort by timestamp descending
        sorted_episodes = sorted(
            self._store.values(),
            key=lambda x: x['timestamp'],
            reverse=True,
        )
        limited = sorted_episodes[:limit]
        # Return copies
        return [episode.copy() for episode in limited]

    def get_by_session(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all episodes for a given session.

        Args:
            session_id: The session ID. If None, uses the current instance's session ID.

        Returns:
            List of episodes for the session
        """
        if session_id is None:
            session_id = self.session_id
        episodes = [
            episode.copy()
            for episode in self._store.values()
            if episode['session_id'] == session_id
        ]
        # Sort by timestamp descending
        episodes.sort(key=lambda x: x['timestamp'], reverse=True)
        return episodes