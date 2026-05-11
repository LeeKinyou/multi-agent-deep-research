import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.database import Task, TaskStatus
from app.models.schemas import TaskStatusEnum

logger = logging.getLogger(__name__)


class StatusManager:
    def __init__(self, db: Session):
        self.db = db

    def update_status(self, task_id: str, status: TaskStatusEnum, error_message: Optional[str] = None) -> Optional[Task]:
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            logger.warning(f"Task {task_id} not found for status update")
            return None

        old_status = task.status
        task.status = TaskStatus(status.value)
        task.updated_at = datetime.utcnow()

        if status == TaskStatusEnum.completed:
            task.completed_at = datetime.utcnow()
        elif status == TaskStatusEnum.failed and error_message:
            task.error_message = error_message

        self.db.commit()
        self.db.refresh(task)

        logger.info(f"Task {task_id} status updated: {old_status} -> {status}")
        return task

    def get_task_status(self, task_id: str) -> Optional[Task]:
        return self.db.query(Task).filter(Task.task_id == task_id).first()

    def is_task_running(self, task_id: str) -> bool:
        task = self.get_task_status(task_id)
        return task is not None and task.status == TaskStatus.running

    def can_transition(self, current_status: TaskStatus, new_status: TaskStatus) -> bool:
        valid_transitions = {
            TaskStatus.planning: [TaskStatus.pending, TaskStatus.cancelled],
            TaskStatus.pending: [TaskStatus.running, TaskStatus.cancelled],
            TaskStatus.running: [TaskStatus.completed, TaskStatus.failed, TaskStatus.cancelled],
            TaskStatus.completed: [],
            TaskStatus.failed: [TaskStatus.pending],
            TaskStatus.cancelled: [],
        }
        return new_status in valid_transitions.get(current_status, [])
