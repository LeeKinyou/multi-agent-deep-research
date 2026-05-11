import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.database import ExecutionLog, Task, TaskResult, TaskStatus
from app.models.schemas import TaskStatusEnum

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self._running_tasks: Dict[str, asyncio.Task] = {}

    def create_task(self, topic: str, depth: str = "standard") -> Task:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = Task(
            task_id=task_id,
            topic=topic,
            status=TaskStatus.planning,
            depth=depth,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        logger.info(f"Task created: {task_id} for topic: {topic}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.db.query(Task).filter(Task.task_id == task_id).first()

    def list_tasks(self, skip: int = 0, limit: int = 50) -> List[Task]:
        return self.db.query(Task).order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        return self.db.query(TaskResult).filter(TaskResult.task_id == task_id).first()

    def save_task_result(
        self,
        task_id: str,
        report_content: str,
        report_format: str = "markdown",
        sources_count: int = 0,
    ) -> TaskResult:
        result = TaskResult(
            task_id=task_id,
            report_content=report_content,
            report_format=report_format,
            sources_count=sources_count,
            word_count=len(report_content),
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        logger.info(f"Task result saved for {task_id}, word count: {result.word_count}")
        return result

    def add_log(
        self,
        task_id: str,
        agent_name: Optional[str] = None,
        step_name: Optional[str] = None,
        log_level: str = "info",
        message: Optional[str] = None,
        validation_event: bool = False,
    ) -> ExecutionLog:
        log = ExecutionLog(
            task_id=task_id,
            agent_name=agent_name,
            step_name=step_name,
            log_level=log_level,
            message=message,
            validation_event=1 if validation_event else 0,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_task_logs(self, task_id: str, limit: int = 100) -> List[ExecutionLog]:
        return (
            self.db.query(ExecutionLog)
            .filter(ExecutionLog.task_id == task_id)
            .order_by(ExecutionLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    async def execute_task(
        self,
        task_id: str,
        execution_func: Callable,
        *args,
        **kwargs,
    ) -> None:
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found for execution")
            return

        if task.status not in [TaskStatus.pending, TaskStatus.planning]:
            logger.warning(f"Task {task_id} is not in executable state: {task.status}")
            return

        self.add_log(task_id, message="Task execution started", log_level="info")

        try:
            task.status = TaskStatus.running
            task.updated_at = datetime.utcnow()
            self.db.commit()

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: execution_func(*args, **kwargs))

            self.save_task_result(task_id, report_content=str(result))
            task.status = TaskStatus.completed
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            self.db.commit()

            self.add_log(task_id, message="Task execution completed", log_level="info")
            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
            task.status = TaskStatus.failed
            task.error_message = str(e)
            task.updated_at = datetime.utcnow()
            self.db.commit()

            self.add_log(task_id, message=f"Task failed: {str(e)}", log_level="error")

        finally:
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

    def cancel_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False

        if task.status not in [TaskStatus.planning, TaskStatus.pending, TaskStatus.running]:
            logger.warning(f"Task {task_id} cannot be cancelled, current status: {task.status}")
            return False

        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            del self._running_tasks[task_id]

        task.status = TaskStatus.cancelled
        task.updated_at = datetime.utcnow()
        self.db.commit()

        self.add_log(task_id, message="Task cancelled by user", log_level="warning")
        logger.info(f"Task {task_id} cancelled")
        return True

    def start_task_execution(self, task_id: str, execution_func: Callable, *args, **kwargs) -> None:
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = TaskStatus.pending
        task.updated_at = datetime.utcnow()
        self.db.commit()

        async_task = asyncio.create_task(self.execute_task(task_id, execution_func, *args, **kwargs))
        self._running_tasks[task_id] = async_task
        logger.info(f"Task {task_id} scheduled for execution")
