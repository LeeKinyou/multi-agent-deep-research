import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    PLAN_GENERATED = "plan.generated"
    PLAN_CONFIRMED = "plan.confirmed"
    PLAN_MODIFIED = "plan.modified"
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    LOG_ENTRY = "log.entry"


class EventBus:
    _instance = None
    _subscribers: Dict[EventType, List[Callable]] = {}
    _event_history: List[Dict[str, Any]] = []
    _max_history = 1000

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
        return cls._instance

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    async def publish(self, event_type: EventType, data: Dict[str, Any]) -> None:
        event = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        logger.info(f"Event published: {event_type.value}")

        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in event callback for {event_type.value}: {str(e)}")

    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        if event_type:
            filtered = [e for e in self._event_history if e["type"] == event_type.value]
            return filtered[-limit:]
        return self._event_history[-limit:]

    def clear_history(self) -> None:
        self._event_history.clear()


event_bus = EventBus()
