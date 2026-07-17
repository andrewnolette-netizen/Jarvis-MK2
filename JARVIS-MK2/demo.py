#!/usr/bin/env python3
"""
Demonstration of JARVIS-MK2's full pipeline:
Goal -> Planner -> Decision Engine -> Critic -> Executor -> Memory
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from brain.planner import Planner
from brain.decision_engine import DecisionEngine
from brain.critic import Critic
from brain.executor import Executor
from tasks.task_manager import TaskManager
from memory.memory_manager import memory_manager

async def main():
    print("🚀 JARVIS-MK2 Full Pipeline Demo")
    print("=" * 50)

    # Initialize core components
    task_manager = TaskManager()
    planner = Planner(task_manager=task_manager)
    decision_engine = DecisionEngine()
    critic = Critic()
    executor = Executor(task_manager=task_manager)

    # Step 1: Define a goal
    goal = "Organize my project files and backup important data"
    print(f"\n🎯 Goal: {goal}")

    # Step 2: Planner creates a plan
    print("\n📋 Step 1: Planner creating plan...")
    plan = await planner.create_plan(goal)
    print(f"   Planner generated {len(plan)} tasks:")
    for i, task in enumerate(plan, 1):
        print(f"   {i}. [{task['priority']}] {task['title']}")

    # Step 3: Decision Engine prioritizes tasks (if multiple)
    print("\n⚖️  Step 2: Decision Engine prioritizing tasks...")
    if len(plan) > 1:
        # Convert plan to options for decision engine
        options = []
        for task in plan:
            options.append({
                "priority": task["priority"],
                "risk": 1,  # Assume low risk for demo
                "dependencies": [],  # Assume no dependencies for demo
                "action": task["title"],
                "task_id": task["id"]
            })
        decision = decision_engine.make_decision(options)
        print(f"   Selected task: {decision['action']} (ID: {next(t['id'] for t in plan if t['title'] == decision['action'])})")
        # For demo, we'll just execute all tasks in priority order
        # Sort by priority (descending) then by decision score
        sorted_tasks = sorted(plan, key=lambda t: (-t["priority"], t.get("score", 0)))
    else:
        sorted_tasks = plan

    # Step 4: Critic reviews the plan
    print("\n🔍 Step 3: Critic reviewing plan...")
    review = critic.review_plan(plan)
    print(f"   Approved: {review.get('approved', False)}")
    print(f"   Confidence: {review.get('confidence', 0):.2f}")
    if review.get("issues"):
        print(f"   Issues found: {len(review['issues'])}")
        for issue in review["issues"][:2]:  # Show first 2 issues
            print(f"     - {issue}")
    if review.get("suggestions"):
        print(f"   Suggestions: {len(review['suggestions'])}")
        for sugg in review["suggestions"][:2]:  # Show first 2 suggestions
            print(f"     - {sugg}")

    # Step 5: Executor runs the tasks
    print("\n⚙️  Step 4: Executor running tasks...")
    executed_count = 0
    for task_info in sorted_tasks:
        task_id = task_info["id"]
        print(f"   Executing: {task_info['title']} (ID: {task_id})")

        # Retrieve the actual task object from task manager
        task = await task_manager.get_task(task_id)
        if task:
            success = await executor.execute_task(task)
            if success:
                print(f"     ✅ Success")
                executed_count += 1
            else:
                print(f"     ❌ Failed")
        else:
            print(f"     ⚠️  Task not found in manager")

    print(f"\n📊 Execution Summary: {executed_count}/{len(sorted_tasks)} tasks completed successfully")

    # Step 6: Check memory for results
    print("\n🧠 Step 5: Memory system update...")

    # Check recent tasks in short-term memory
    recent_tasks = []
    for task_info in sorted_tasks:
        task_id = task_info["id"]
        recent_key = f"recent_task_{task_id}"
        recent = memory_manager.retrieve(recent_key)
        if recent:
            recent_tasks.append(recent)

    print(f"   Recent task memories stored: {len(recent_tasks)}")
    for mem in recent_tasks[:2]:  # Show first 2
        print(f"     - {mem.get('title')}: {mem.get('status')} at {mem.get('timestamp', 0):.0f}")

    # Check episodic memory
    episodes = memory_manager.episodic.get_by_session()
    completed_episodes = [ep for ep in episodes if ep.get("event_type") == "task_completed"]
    failed_episodes = [ep for ep in episodes if ep.get("event_type") == "task_failed"]
    print(f"   Episodic memories: {len(completed_episodes)} completed, {len(failed_episodes)} failed")

    if completed_episodes:
        latest = completed_episodes[-1]
        print(f"   Latest completion: {latest.get('data', {}).get('title')} (importance: {latest.get('importance', 0):.2f})")

    # Show overall memory stats
    print(f"\n📈 Memory Statistics:")
    print(f"   Short-term items: {len(memory_manager.short_term._store)}")
    print(f"   Long-term items: {len(memory_manager.long_term._store)}")
    print(f"   Episodic items: {len(memory_manager.episodic._store)}")

    print("\n✅ Demo complete!")
    print("   JARVIS-MK2 successfully processed a goal through the full cognitive pipeline.")

if __name__ == "__main__":
    asyncio.run(main())