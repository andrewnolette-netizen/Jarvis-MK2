"""
Tests for the executor module.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from brain.executor import Executor
from brain.planner import Planner
from tasks.task_manager import TaskManager
from memory.memory_manager import memory_manager


async def test_executor_basic():
    """Test that the executor can be created and execute a simple task."""
    print("Testing Executor...")

    # Create instances
    task_manager = TaskManager()
    planner = Planner(task_manager=task_manager)
    executor = Executor(task_manager=task_manager)

    # Create a simple plan
    plan = await planner.create_plan("Test goal for execution")
    assert len(plan) > 0, "Planner should create at least one task"
    task_info = plan[0]
    task_id = task_info["id"]
    print(f"Created task: {task_id}")

    # Retrieve the task from the task manager
    task = await task_manager.get_task(task_id)
    assert task is not None, "Task should exist in task manager"
    print(f"Retrieved task: {task.title}")

    # Execute the task
    result = await executor.execute_task(task)
    assert result is True, "Task execution should succeed"
    print(f"Task execution result: {result}")

    # Check that the task is now in SUCCESS state
    updated_task = await task_manager.get_task(task_id)
    assert updated_task.status.name == "SUCCESS", f"Expected SUCCESS, got {updated_task.status}"
    print(f"Task status after execution: {updated_task.status}")

    # Check that memory was updated
    # Look for recent task in memory
    recent_key = f"recent_task_{task_id}"
    recent_memory = memory_manager.retrieve(recent_key)
    assert recent_memory is not None, "Recent task memory should be stored"
    assert recent_memory.get("status") == "success", "Memory should reflect success"
    print(f"Recent memory: {recent_memory}")

    # Check episodic memory for completion event
    episodes = memory_manager.episodic.get_by_session()
    completion_episodes = [
        ep for ep in episodes if ep.get("event_type") == "task_completed"
    ]
    assert len(completion_episodes) > 0, "Should have a task completion episode"
    print(f"Found {len(completion_episodes)} completion episodes")

    print("Executor test passed!")


# async def test_executor_pipeline():
#     """Test a simple pipeline: plan -> decide -> critic -> execute -> memory."""
#     print("\nTesting Pipeline...")
#
#     # Create components
#     task_manager = TaskManager()
#     planner = Planner(task_manager=task_manager)
#     decision_engine = DecisionEngine()
#     critic = Critic()
#     executor = Executor(task_manager=task_manager)
#
#     # 1. Plan
#     # goal = "Create a backup plan and execute it"
#     # plan = await planner.create_plan(goal)
#     # assert len(plan) >= 1, "Should have a plan"
#     # print(f"Planner created {len(plan)} tasks")
#
#     # 2. Decide (prioritize tasks)
#     # For simplicity, we'll just use the first task
#     # task_info = plan[0]
#     # task_id = task_info["id"]
#     # task = await task_manager.get_task(task_id)
#     # assert task is not None
#
#     # 3. Critic (review the plan / task)
#     # review = critic.plan([task_info])  # Pass the task info as a plan
#     # We don't necessarily need to act on the critic's review for this test
#     # print(f"Critic review: approved={review.get('approved', False)}")
#
#     # 4. Execute
#     # success = await executor.execute_task(task)
#     # assert success is True, "Task should execute successfully"
#
#     # 5. Memory
#     # # Check that the task is in memory
#     # recent_key = f"recent_task_{task_id}"
#     # recent = memory_manager.receive(recent_key)
#     # assert recent is not None
#     # assert recent.get("status") == "success"
#
#     print("Pipeline test skipped for now")


async def main():
    """Run all tests."""
    await test_executor_basic()
    # await test_executor_pipeline()
    print("\n🎉 All executor tests passed!")


if __name__ == "__main__":
    asyncio.run(main())