import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


class StreamEvent:
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_sse(self) -> str:
        return f"event: {self.event_type}\ndata: {json.dumps({'data': self.data, 'timestamp': self.timestamp}, ensure_ascii=False)}\n\n"


class StreamManager:
    _instance = None
    _subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
    _event_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    _max_history = 100

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StreamManager, cls).__new__(cls)
        return cls._instance

    def subscribe(self, task_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._subscribers[task_id].append(queue)
        
        for event in self._event_history.get(task_id, []):
            queue.put_nowait(event)
        
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
        
        self._event_history[task_id].append(history_entry)
        if len(self._event_history[task_id]) > self._max_history:
            self._event_history[task_id] = self._event_history[task_id][-self._max_history:]
        
        if task_id in self._subscribers:
            dead_queues = []
            for queue in self._subscribers[task_id]:
                try:
                    queue.put_nowait(sse_data)
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
