"""
Basic tests for JARVIS-MK2.
"""

import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.config import Config
from core.logger import get_logger
from core.events import EventManager
from core.controller import Controller


class TestConfig(unittest.TestCase):
    """Test configuration management."""

    def test_config_singleton(self):
        """Test that Config is a singleton."""
        config1 = Config()
        config2 = Config()
        self.assertIs(config1, config2)

    def test_get_default(self):
        """Test getting a default configuration value."""
        config = Config()
        self.assertEqual(config.get("system.name"), "JARVIS-MK2")
        self.assertEqual(config.get("system.version"), "0.1.0")


class TestLogger(unittest.TestCase):
    """Test logging functionality."""

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test")
        self.assertIsNotNone(logger)


class TestEventManager(unittest.TestCase):
    """Test event management."""

    def test_event_singleton(self):
        """Test that EventManager is a singleton."""
        em1 = EventManager()
        em2 = EventManager()
        self.assertIs(em1, em2)

    def test_subscribe_and_publish(self):
        """Test subscribing to and publishing events."""
        em = EventManager()
        received_data = []

        def callback(event):
            received_data.append(event.data)

        em.subscribe("test_event", callback)
        em.publish("test_event", "test_data")
        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0], "test_data")


class TestController(unittest.TestCase):
    """Test application controller."""

    def test_controller_singleton(self):
        """Test that Controller is a singleton."""
        c1 = Controller()
        c2 = Controller()
        self.assertIs(c1, c2)


if __name__ == "__main__":
    unittest.main()