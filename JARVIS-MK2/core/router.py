"""
Routing module for JARVIS-MK2.
Routes requests to appropriate modules based on intent or command.
"""

from typing import Any, Callable, Dict, Optional

from core.logger import get_logger
from core.events import EventManager, publish

logger = get_logger(__name__)


class Route:
    """Represents a route pattern and its handler."""

    def __init__(self, pattern: str, handler: Callable, methods: list[str] = None):
        """
        Initialize a route.

        Args:
            pattern: URL or command pattern to match
            handler: Function to handle the request
            methods: List of HTTP methods this route responds to (for web)
        """
        self.pattern = pattern
        self.handler = handler
        self.methods = methods or ['GET']  # Default to GET for simplicity


class Router:
    """URL/Command router for JARVIS-MK2."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Router, cls).__new__(cls)
            cls._instance._routes: Dict[str, Route] = {}
            cls._instance._event_manager = EventManager()
        return cls._instance

    def add_route(self, pattern: str, handler: Callable, methods: list[str] = None) -> None:
        """
        Add a route to the router.

        Args:
            pattern: Pattern to match
            handler: Handler function
            methods: HTTP methods (for web routes)
        """
        route = Route(pattern, handler, methods)
        self._routes[pattern] = route
        logger.debug(f"Added route: {pattern}")

    def remove_route(self, pattern: str) -> None:
        """
        Remove a route from the router.

        Args:
            pattern: Pattern to remove
        """
        if pattern in self._routes:
            del self._routes[pattern]
            logger.debug(f"Removed route: {pattern}")

    def get_route(self, pattern: str) -> Optional[Route]:
        """
        Get a route by pattern.

        Args:
            pattern: Pattern to look up

        Returns:
            Route if found, None otherwise
        """
        return self._routes.get(pattern)

    def handle_request(self, path: str, method: str = 'GET', **kwargs) -> Any:
        """
        Handle an incoming request.

        Args:
            path: Request path
            method: HTTP method
            **kwargs: Additional arguments

        Returns:
            Response from handler

        Raises:
            KeyError: If no matching route is found
        """
        # Look for exact match first
        if path in self._routes:
            route = self._routes[path]
            if method in route.methods:
                logger.debug(f"Handling request for {path} with method {method}")
                return route.handler(**kwargs)
            else:
                logger.warning(f"Method {method} not allowed for route {path}")
                raise ValueError(f"Method {method} not allowed for route {path}")

        # If no exact match, we could implement pattern matching here
        # For now, we'll just raise not found
        logger.warning(f"No route found for {path}")
        raise KeyError(f"No route found for {path}")

    def get_routes(self) -> Dict[str, Route]:
        """Get all registered routes."""
        return self._routes.copy()


# Global router instance
router = Router()


def add_route(pattern: str, handler: Callable, methods: list[str] = None) -> None:
    """Convenience function to add a route."""
    router.add_route(pattern, handler, methods)


def remove_route(pattern: str) -> None:
    """Convenience function to remove a route."""
    router.remove_route(pattern)


def handle_request(path: str, method: str = 'GET', **kwargs) -> Any:
    """Convenience function to handle a request."""
    return router.handle_request(path, method, **kwargs)