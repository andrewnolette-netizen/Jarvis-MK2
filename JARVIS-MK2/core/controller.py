"""
Main controller for JARVIS-MK2.
Manages the application lifecycle and coordinates modules.
"""

import asyncio
import signal
import sys
from typing import List

from core.config import config
from core.logger import get_logger, setup_logging
from core.events import EventManager, publish
from core.router import Router

logger = get_logger(__name__)


class Controller:
    """Main application controller."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Controller, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance._running = False
            cls._instance._tasks: list[asyncio.Task] = []
            cls._instance._shutdown_event = asyncio.Event()
            cls._instance._modules: list = []
        return cls._instance

    def __init__(self):
        # Note: _initialized is set to False in __new__
        self.config = config
        self.logger = get_logger(__name__)
        self.event_manager = EventManager()
        self.router = Router()
        self.loop = None

    def initialize(self) -> None:
        """Initialize the application and all modules."""
        if self._initialized:
            self.logger.warning("Controller already initialized")
            return

        self.logger.info("Initializing JARVIS-MK2...")
        self.logger.info(f"Version: {self.config.get('system.version')}")
        self.logger.info(f"Debug mode: {self.config.get('system.debug')}")

        # Set up logging
        setup_logging()

        # Initialize core components
        # Already done in __init__

        # Note: event system and router are already instantiated in __init__
        # So we don't need to do anything here for them.

        self._initialized = True
        self.logger.info("Initialization complete")

    def start(self) -> None:
        """Start the application."""
        if not self._initialized:
            self.initialize()

        if self._running:
            self.logger.warning("Controller already running")
            return

        self.logger.info("Starting JARVIS-MK2...")
        self._running = True

        # Publish application started event
        publish("application.started", source="Controller")

        # Main event loop
        try:
            self.loop.run_until_complete(self._shutdown_event.wait())
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        if not self._running:
            return

        self.logger.info("Shutting down JARVIS-MK2...")
        self._running = False

        # Publish application stopping event
        publish("application.stopping", source="Controller")

        # Cancel all running tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            # We need to run the asyncio event loop to wait for the tasks
            # We'll run the loop until the tasks are done.
            # We'll wait for all tasks to complete, ignoring exceptions.
            self.loop.run_until_complete(asyncio.gather(*self._tasks, return_exceptions=True))

        # Shutdown modules
        self._shutdown_modules()

        # Clear event handlers
        self.event_manager = EventManager()

        self._shutdown_event.set()
        self.logger.info("Shutdown complete")

    def _shutdown_modules(self) -> None:
        """Shutdown all loaded modules."""
        self.logger.info("Shutting down modules...")
        # Placeholder for module shutdown logic
        pass

    def run(self) -> None:
        """Run the application (blocking)."""
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        try:
            self.start()
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.loop.close()


# Global controller instance
controller = Controller()


def main() -> None:
    """Main entry point for the application."""
    controller.run()


if __name__ == "__main__":
    main()