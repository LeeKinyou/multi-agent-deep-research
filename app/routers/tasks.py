import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.database import Task, TaskResult, TaskStatus, get_db
from app.models.schemas import (
    ExecutionLogResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskResultResponse,
    TaskStatusEnum,
)
from app.services.event_bus import EventType, event_bus
from app.services.status_manager import StatusManager
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    task_service = TaskService(db)
    task = task_service.create_task(topic=task_data.topic, depth=task_data.depth)

    await event_bus.publish(EventType.TASK_CREATED, {
        "task_id": task.task_id,
        "topic": task.topic,
    })

    return TaskResponse(
        task_id=task.task_id,
        topic=task.topic,
        status=TaskStatusEnum(task.status.value),
        depth=task.depth,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
    )


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    task_service = TaskService(db)
    tasks = task_service.list_tasks(skip=skip, limit=limit)
    total = db.query(Task).count()

    return TaskListResponse(
        tasks=[
            TaskResponse(
                task_id=t.task_id,
                topic=t.topic,
                status=TaskStatusEnum(t.status.value),
                depth=t.depth,
                created_at=t.created_at,
                updated_at=t.updated_at,
                completed_at=t.completed_at,
                error_message=t.error_message,
            )
            for t in tasks
        ],
        total=total,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    task_service = TaskService(db)
    task = task_service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return TaskResponse(
        task_id=task.task_id,
        topic=task.topic,
        status=TaskStatusEnum(task.status.value),
        depth=task.depth,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
    )


@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str, db: Session = Depends(get_db)):
    task_service = TaskService(db)
    task = task_service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status != TaskStatus.completed:
        raise HTTPException(
            status_code=400,
            detail=f"Task is not completed. Current status: {task.status.value}",
        )

    result = task_service.get_task_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Result not found for task {task_id}")

    return TaskResultResponse(
        task_id=result.task_id,
        report_content=result.report_content,
        report_format=result.report_format,
        sources_count=result.sources_count,
        word_count=result.word_count,
        created_at=result.created_at,
    )


@router.get("/{task_id}/logs", response_model=List[ExecutionLogResponse])
async def get_task_logs(
    task_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    task_service = TaskService(db)
    task = task_service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    logs = task_service.get_task_logs(task_id, limit=limit)
    return [
        ExecutionLogResponse(
            id=log.id,
            task_id=log.task_id,
            agent_name=log.agent_name,
            step_name=log.step_name,
            log_level=log.log_level,
            message=log.message,
            validation_event=bool(log.validation_event),
            timestamp=log.timestamp,
        )
        for log in logs
    ]


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: Session = Depends(get_db)):
    task_service = TaskService(db)
    success = task_service.cancel_task(task_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} cannot be cancelled",
        )

    await event_bus.publish(EventType.TASK_CANCELLED, {"task_id": task_id})

    return {"message": f"Task {task_id} cancelled successfully"}
