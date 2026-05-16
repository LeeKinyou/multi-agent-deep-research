import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 100
MAX_HISTORY = 100


class StreamEvent:
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_sse(self) -> str:
        return f"event: {self.event_type}\ndata: {json.dumps({'data': self.data, 'timestamp': self.timestamp}, ensure_ascii=False)}\n\n"


class StreamManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(StreamManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._event_history: Dict[str, List[Dict[str, Any]]] = {}
        self._max_history = MAX_HISTORY

    def subscribe(self, task_id: str) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(queue)

        for event in self._event_history.get(task_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"Queue full for task {task_id}, dropping old history event")

        logger.info(f"New subscriber for task {task_id}")
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue):
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[task_id]:
                del self._subscribers[task_id]

    async def publish(self, task_id: str, event_type: str, data: Dict[str, Any]):
        event = StreamEvent(event_type, data)
        sse_data = event.to_sse()

        history_entry = {
            "event_type": event_type,
            "data": data,
            "timestamp": event.timestamp,
        }

        if task_id not in self._event_history:
            self._event_history[task_id] = []
        self._event_history[task_id].append(history_entry)
        if len(self._event_history[task_id]) > self._max_history:
            self._event_history[task_id] = self._event_history[task_id][-self._max_history:]

        if task_id in self._subscribers:
            dead_queues = []
            for queue in self._subscribers[task_id]:
                try:
                    queue.put_nowait(sse_data)
                except asyncio.QueueFull:
                    logger.warning(
                        f"Backpressure: queue full for task {task_id}, "
                        f"dropping oldest event (size={queue.qsize()})"
                    )
                    try:
                        queue.get_nowait()
                        queue.put_nowait(sse_data)
                    except Exception:
                        dead_queues.append(queue)
                except Exception as e:
                    logger.error(f"Error publishing to queue for task {task_id}: {e}")
                    dead_queues.append(queue)

            for queue in dead_queues:
                try:
                    self._subscribers[task_id].remove(queue)
                except ValueError:
                    pass

    async def publish_agent_thinking(self, task_id: str, agent_name: str, thinking: str, step: str = ""):
        await self.publish(task_id, "agent_thinking", {
            "agent_name": agent_name,
            "thinking": thinking,
            "step": step,
        })

    async def publish_agent_start(self, task_id: str, agent_name: str, task_description: str):
        await self.publish(task_id, "agent_start", {
            "agent_name": agent_name,
            "task_description": task_description,
        })

    async def publish_agent_complete(self, task_id: str, agent_name: str, output: str):
        await self.publish(task_id, "agent_complete", {
            "agent_name": agent_name,
            "output": output,
        })

    async def publish_progress(self, task_id: str, current_step: int, total_steps: int, message: str):
        await self.publish(task_id, "progress", {
            "current_step": current_step,
            "total_steps": total_steps,
            "message": message,
            "percent": int((current_step / total_steps) * 100) if total_steps > 0 else 0,
        })

    async def publish_task_status(self, task_id: str, status: str, message: str):
        await self.publish(task_id, "task_status", {
            "status": status,
            "message": message,
        })

    async def publish_error(self, task_id: str, error: str):
        await self.publish(task_id, "error", {
            "error": error,
        })

    async def publish_complete(self, task_id: str, result: str):
        await self.publish(task_id, "complete", {
            "result": result,
        })

    def get_event_history(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self._event_history.get(task_id, [])[-limit:]

    def clear_task(self, task_id: str):
        if task_id in self._subscribers:
            del self._subscribers[task_id]
        if task_id in self._event_history:
            del self._event_history[task_id]


stream_manager = StreamManager()
