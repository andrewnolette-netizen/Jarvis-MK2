# --------------------------------------------------------------
# jarvis_core/service.py
# Thin JSON‑RPC façade over the JARVIS‑MK2 core.
# Publishes status events on a PUB socket (port 5556) for the GUI.
# --------------------------------------------------------------
import asyncio
import json
import time
import uuid
from typing import Any, Dict

import zmq
import zmq.asyncio

# ---- Core imports (your existing modules) ----
from brain.planner import Planner
from brain.decision_engine import DecisionEngine
from brain.critic import Critic
from brain.executor import Executor
from tasks.task_manager import TaskManager
from memory.memory_manager import memory_manager
from ai.mock_provider import MockProvider   # swap for OllamaProvider later


class JarvisService:
    """
    RPC service that the UI and Voice layers talk to.
    Uses ZeroMQ REQ/REP for commands and PUB/SUB for events.
    """

    def __init__(self, port: int = 5555, pub_port: int = 5556):
        self.ctx = zmq.asyncio.Context()
        # ---- REP socket for RPC calls ----
        self.socket = self.ctx.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{port}")

        # ---- PUB socket for broadcasting events ----
        self.pub_ctx = zmq.asyncio.Context()
        self.pub_socket = self.pub_ctx.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{pub_port}")

        # ---- Initialise core singletons ----
        self.task_mgr = TaskManager()
        self.planner = Planner(task_manager=self.task_mgr)
        self.decider = DecisionEngine()
        self.critic = Critic()
        self.exec = Executor(task_manager=self.task_mgr)
        self.memory = memory_manager
        self.ai = MockProvider()          # <-- change to OllamaProvider if you have Ollama running

        print(f"[🟢] JARVIS Service listening (RPC on {port}, PUBSUB on {pub_port})")

    # -----------------------------------------------------------------
    # Helper: safely call a coroutine and return a JSON‑serialisable dict
    # -----------------------------------------------------------------
    async def _safe_call(self, coro):
        try:
            result = await coro
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # -----------------------------------------------------------------
    # Publish an event (fire‑and‑forget)
    # -----------------------------------------------------------------
    async def _publish(self, event: str, data: Dict[str, Any]):
        msg = {
            "event": event,
            "timestamp": time.time(),
            "data": data,
        }
        try:
            await self.pub_socket.send_string(json.dumps(msg))
        except Exception:
            # Never let a publishing error kill the service
            pass

    # -----------------------------------------------------------------
    # RPC METHODS – each maps to a core capability
    # -----------------------------------------------------------------
    async def plan_goal(self, goal: str) -> dict:
        plan = await self.planner.create_plan(goal)
        return {"plan": plan}

    async def decide(self, options: list[dict]) -> dict:
        decision = self.decider.make_decision(options)
        return {"decision": decision}

    async def critique(self, payload: dict) -> dict:
        if "plan" in payload:
            review = self.critic.plan(payload["plan"])
        else:
            review = self.critic.review_decision(payload["decision"])
        return {"review": review}

    async def execute_task(self, task_desc: dict) -> dict:
        """
        task_desc must contain at least:
            - title
            - description (optional)
            - priority (int 1‑3)
        """
        from tasks.task_manager import Task, TaskStatus

        # Create a Task object and make sure it exists in the manager
        task = Task(
            title=task_desc["title"],
            description=task_desc.get("description", ""),
            priority=task_desc.get("priority", 2),
        )
        await self.task_mgr.create_task(
            title=task.title,
            description=task.description,
            priority=task.priority,
        )

        # Notify UI that we’re starting
        await self._publish("task_started", {"title": task.title, "task_id": task.id})

        # Run the task via the executor
        success = await self.exec.execute_task(task)

        # Fetch final state
        updated = await self.task_mgr.get_task(task.id)
        final_status = getattr(
            getattr(updated, "status", None), "name", str(updated.status)
        )

        # Notify UI of outcome
        if success:
            await self._publish(
                "task_completed",
                {"title": task.title, "task_id": task.id},
            )
        else:
            await self._publish(
                "task_failed",
                {
                    "title": task.title,
                    "task_id": task.id,
                    "error": "Task failed after retries",
                },
            )

        return {
            "task_id": task.id,
            "success": success,
            "final_status": final_status,
        }

    async def memory_store(self, payload: dict) -> dict:
        key = payload["key"]
        value = payload["value"]
        long = payload.get("long_term", False)
        imp = payload.get("importance", 0.5)
        tags = payload.get("tags", [])
        self.memory.store(key, value, long_term=long, importance=imp, tags=tags)
        return {"stored": True}

    async def memory_recall(self, payload: dict) -> dict:
        key = payload["key"]
        val = self.memory.retrieve(key)
        return {"value": val}

    async def memory_search(self, payload: dict) -> dict:
        query = payload["query"]
        hits = self.memory.search(query)
        return {"hits": hits}

    async def memory_episode(self, payload: dict) -> dict:
        eid = self.memory.store_episode(
            event_type=payload["event_type"],
            data=payload["data"],
            importance=payload.get("importance", 0.5),
            tags=payload.get("tags", []),
        )
        return {"episode_id": eid}

    async def ai_generate(self, payload: dict) -> dict:
        txt = await self.ai.generate(
            prompt=payload["prompt"],
            max_tokens=payload.get("max_tokens"),
            temperature=payload.get("temperature", 0.7),
        )
        return {"text": txt}

    async def ai_classify(self, payload: dict) -> dict:
        probs = await self.ai.classify(
            text=payload["text"],
            categories=payload["categories"],
        )
        return {"probabilities": probs}

    # -----------------------------------------------------------------
    # Main loop – receive JSON‑RPC request, route to method, send reply
    # -----------------------------------------------------------------
    async def run(self):
        while True:
            try:
                raw = await self.socket.recv_string()
                msg = json.loads(raw)
                method = msg.get("method")
                params = msg.get("params", {})
                req_id = msg.get("id", str(uuid.uuid4()))

                # Dispatch
                if method == "plan_goal":
                    resp = await self._safe_call(self.plan_goal(**params))
                elif method == "decide":
                    resp = await self._safe_call(self.decide(**params))
                elif method == "critique":
                    resp = await self._safe_call(self.critique(**params))
                elif method == "execute_task":
                    resp = await self._safe_call(self.execute_task(**params))
                elif method == "memory_store":
                    resp = await self._safe_call(self.memory_store(**params))
                elif method == "memory_recall":
                    resp = await self._safe_call(self.memory_recall(**params))
                elif method == "memory_search":
                    resp = await self._safe_call(self.memory_search(**params))
                elif method == "memory_episode":
                    resp = await self._safe_call(self.memory_episode(**params))
                elif method == "ai_generate":
                    resp = await self._safe_call(self.ai_generate(**params))
                elif method == "ai_classify":
                    resp = await self._safe_call(self.ai_classify(**params))
                else:
                    resp = {"ok": False, "error": f"Unknown method {method}"}

                out = {"id": req_id, **resp}
                await self.socket.send_string(json.dumps(out))

            except Exception as e:
                # Never crash the service – always send an error frame
                await self.socket.send_string(
                    json.dumps({"id": None, "ok": False, "error": str(e)})
                )