"""
Integration test for JARVIS-MK2 core components.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.controller import Controller
from core.config import Config
from core.logger import get_logger
from core.events import EventManager, subscribe, publish
from brain.planner import Planner
from brain.decision_engine import DecisionEngine
from brain.critic import Critic
from brain.reasoning import Reasoner
from memory.memory_manager import MemoryManager
from tasks.task_manager import TaskManager, TaskStatus


async def test_core_components():
    """Test that core components can be initialized and work together."""
    print("Testing core components...")

    # Test controller
    controller = Controller()
    controller.initialize()  # Not a coroutine anymore
    print("✓ Controller initialized")

    # Test config
    config = Config()
    assert config.get("system.name") == "JARVIS-MK2"
    print("✓ Config working")

    # Test logger
    logger = get_logger("test")
    assert logger is not None
    print("✓ Logger working")

    # Test event manager
    event_manager = EventManager()
    received_events = []

    def test_handler(event):
        received_events.append(event)

    event_manager.subscribe("test.event", test_handler)
    event_manager.publish("test.event", {"data": "test"})
    assert len(received_events) == 1
    assert received_events[0].data == {"data": "test"}
    print("✓ Event manager working")

    # Test planner
    planner = Planner()
    plan = planner.create_plan("Test goal")
    assert "goal" in plan
    assert plan["goal"] == "Test goal"
    print("✓ Planner working")

    # Test decision engine
    decision_engine = DecisionEngine()
    options = [{"priority": 1}, {"priority": 2}]
    decision = decision_engine.make_decision(options)
    assert decision["priority"] == 2  # Should pick higher priority
    print("✓ Decision engine working")

    # Test critic
    critic = Critic()
    decision = {"priority": 1, "selected_at": 12345}
    review = critic.review_decision(decision)
    assert "approved" in review
    print("✓ Critic working")

    # Test reasoner
    reasoner = Reasoner()
    reasoner.add_fact("test_fact", True)
    assert reasoner.query("test_fact") is True
    print("✓ Reasoner working")

    # Test memory manager
    memory_manager = MemoryManager()
    memory_manager.store("test_key", "test_value")
    assert memory_manager.retrieve("test_key") == "test_value"
    print("✓ Memory manager working")

    # Test task manager
    task_manager = TaskManager()
    task = await task_manager.create_task(
        title="Test Task",
        description="A test task",
        priority=1
    )
    assert task.title == "Test Task"
    assert task.status == TaskStatus.CREATED
    print("✓ Task manager working")

    print("\nAll core components tested successfully!")


if __name__ == "__main__":
    asyncio.run(test_core_components())