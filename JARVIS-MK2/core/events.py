"""
Event system for JARVIS-MK2.
Provides publish-subscribe messaging between modules.
"""

import asyncio
import inspect
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Set

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Event:
    """Base event class."""
    name: str
    data: Any = None
    source: str = ""
    timestamp: float = field(default_factory=lambda: _get_time())


def _get_time() -> float:
    """Get the current time, using the event loop if available, otherwise falling back to time.time."""
    try:
        return asyncio.get_event_loop().time()
    except RuntimeError:
        # No event loop running
        return time.time()


class EventManager:
    """Manages event subscriptions and publishing."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventManager, cls).__new__(cls)
            cls._instance._subscribers: dict[str, list[Callable]] = defaultdict(list)
            cls._instance._async_subscribers: dict[str, list[Callable]] = defaultdict(list)
            cls._instance._middleware: list[Callable] = []
            cls._instance._event_history: list[Event] = []
            cls._instance._max_history = 1000
        return cls._instance

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """
        Subscribe to an event.

        Args:
            event_name: Name of the event to subscribe to
            callback: Function to call when event is published
        """
        if asyncio.iscoroutinefunction(callback):
            self._async_subscribers[event_name].append(callback)
        else:
            self._subscribers[event_name].append(callback)
        logger.debug(f"Subscribed to event '{event_name}'")

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """
        Unsubscribe from an event.

        Args:
            event_name: Name of the event to unsubscribe from
            callback: Function to remove
        """
        lists = [
            self._subscribers.get(event_name, []),
            self._async_subscribers.get(event_name, [])
        ]
        for lst in lists:
            try:
                lst.remove(callback)
            except ValueError:
                pass
        logger.debug(f"Unsubscribed from event '{event_name}'")

    def add_middleware(self, middleware: Callable) -> None:
        """
        Add middleware that processes all events.

        Args:
            middleware: Function that takes (event) and returns modified event or None to cancel
        """
        self._middleware.append(middleware)
        logger.debug("Added event middleware")

    def publish(self, event_name: str, data: Any = None, source: str = "") -> None:
        """
        Publish an event synchronously.

        Args:
            event_name: Name of the event to publish
            data: Data to pass to subscribers
            source: Source of the event
        """
        event = Event(name=event_name, data=data, source=source)
        self._process_event(event)

    async def publish_async(self, event_name: str, data: Any = None, source: str = "") -> None:
        """
        Publish an event asynchronously.

        Args:
            event_name: Name of the event to publish
            data: Data to pass to subscribers
            source: Source of the event
        """
        event = Event(name=event_name, data=data, source=source)
        await self._process_event_async(event)

    def _process_event(self, event: Event) -> None:
        """Process an event synchronously."""
        # Apply middleware
        for middleware in self._middleware:
            try:
                result = middleware(event)
                if result is None:
                    # Middleware cancelled the event
                    return
                elif isinstance(result, Event):
                    event = result
            except Exception as e:
                logger.error(f"Error in middleware for event {event.name}: {e}")
                return

        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Call synchronous subscribers
        for callback in self._subscribers[event.name]:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.name}: {e}")

        # Schedule asynchronous subscribers
        for callback in self._async_subscribers[event.name]:
            try:
                asyncio.create_task(callback(event))
            except Exception as e:
                logger.error(f"Error scheduling async event handler for {event.name}: {e}")

        logger.debug(f"Published event '{event.name}' from {event.source}")

    async def _process_event_async(self, event: Event) -> None:
        """Process an event asynchronously."""
        # Apply middleware
        for middleware in self._middleware:
            try:
                result = middleware(event)
                if result is None:
                    # Middleware cancelled the event
                    return
                elif isinstance(result, Event):
                    event = result
            except Exception as e:
                logger.error(f"Error in middleware for event {event.name}: {e}")
                return

        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Call synchronous subscribers
        for callback in self._subscribers[event.name]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # If it's actually a coroutine, schedule it
                    asyncio.create_task(callback(event))
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.name}: {e}")

        # Call asynchronous subscribers
        for callback in self._async_subscribers[event.name]:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in async event handler for {event.name}: {e}")

        logger.debug(f"Published event '{event.name}' from {event.source}")

    def get_event_history(self, event_name: str = None, limit: int = 100) -> List[Event]:
        """
        Get event history.

        Args:
            event_name: Filter by event name (None for all)
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        if event_name:
            filtered = [e for e in self._event_history if e.name == event_name]
            return filtered[-limit:]
        else:
            return self._event_history[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()


# Global event manager instance
event_manager = EventManager()


def subscribe(event_name: str, callback: Callable) -> None:
    """Convenience function to subscribe to an event."""
    event_manager.subscribe(event_name, callback)


def unsubscribe(event_name: str, callback: Callable) -> None:
    """Convenience function to unsubscribe from an event."""
    event_manager.unsubscribe(event_name, callback)


def publish(event_name: str, data: Any = None, source: str = "") -> None:
    """Convenience function to publish an event."""
    event_manager.publish(event_name, data, source)


async def publish_async(event_name: str, data: Any = None, source: str = "") -> None:
    """Convenience function to publish an event asynchronously."""
    await event_manager.publish_async(event_name, data, source)