import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import PlanStatus, TaskStatus, get_db
from app.models.schemas import (
    PlanConfirmRequest,
    PlanStatusEnum,
    ResearchPlanCreate,
    ResearchPlanResponse,
    TaskStatusEnum,
)
from app.services.event_bus import EventType, event_bus
from app.services.plan_service import PlanService
from app.services.status_manager import StatusManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks/{task_id}/plan", tags=["plans"])


@router.get("/", response_model=ResearchPlanResponse)
async def get_plan(task_id: str, db: Session = Depends(get_db)):
    plan_service = PlanService(db)
    plan = plan_service.get_plan(task_id)

    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found for task {task_id}")

    return ResearchPlanResponse(
        id=plan.id,
        task_id=plan.task_id,
        plan_content=json.loads(plan.plan_content),
        version=plan.version,
        status=PlanStatusEnum(plan.status.value),
        created_at=plan.created_at,
        confirmed_at=plan.confirmed_at,
    )


@router.post("/", response_model=ResearchPlanResponse, status_code=201)
async def create_plan(
    task_id: str,
    plan_data: ResearchPlanCreate,
    db: Session = Depends(get_db),
):
    plan_service = PlanService(db)
    status_manager = StatusManager(db)

    task = status_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    existing_plan = plan_service.get_plan(task_id)
    if existing_plan:
        raise HTTPException(status_code=400, detail=f"Plan already exists for task {task_id}")

    plan = plan_service.create_plan(
        task_id=task_id,
        plan_content=plan_data.plan_content,
        version=plan_data.version,
    )

    await event_bus.publish(EventType.PLAN_GENERATED, {
        "task_id": task_id,
        "plan_version": plan.version,
    })

    return ResearchPlanResponse(
        id=plan.id,
        task_id=plan.task_id,
        plan_content=json.loads(plan.plan_content),
        version=plan.version,
        status=PlanStatusEnum(plan.status.value),
        created_at=plan.created_at,
        confirmed_at=plan.confirmed_at,
    )


@router.post("/confirm", response_model=ResearchPlanResponse)
async def confirm_plan(
    task_id: str,
    request: PlanConfirmRequest,
    db: Session = Depends(get_db),
):
    plan_service = PlanService(db)
    status_manager = StatusManager(db)

    plan = plan_service.get_plan(task_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found for task {task_id}")

    if plan.status == PlanStatus.confirmed:
        raise HTTPException(status_code=400, detail="Plan is already confirmed")

    updated_plan = plan_service.confirm_plan(task_id, request)

    if request.confirmed:
        status_manager.update_status(task_id, TaskStatusEnum.pending)
        await event_bus.publish(EventType.PLAN_CONFIRMED, {
            "task_id": task_id,
        })
    else:
        await event_bus.publish(EventType.PLAN_MODIFIED, {
            "task_id": task_id,
            "modifications": request.modifications,
        })

    return ResearchPlanResponse(
        id=updated_plan.id,
        task_id=updated_plan.task_id,
        plan_content=json.loads(updated_plan.plan_content),
        version=updated_plan.version,
        status=PlanStatusEnum(updated_plan.status.value),
        created_at=updated_plan.created_at,
        confirmed_at=updated_plan.confirmed_at,
    )


@router.put("/", response_model=ResearchPlanResponse)
async def update_plan(
    task_id: str,
    plan_content: Dict[str, Any],
    db: Session = Depends(get_db),
):
    plan_service = PlanService(db)

    plan = plan_service.get_plan(task_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found for task {task_id}")

    if plan.status == PlanStatus.confirmed:
        raise HTTPException(status_code=400, detail="Cannot update a confirmed plan")

    updated_plan = plan_service.update_plan(task_id, plan_content)

    await event_bus.publish(EventType.PLAN_MODIFIED, {
        "task_id": task_id,
        "new_version": updated_plan.version,
    })

    return ResearchPlanResponse(
        id=updated_plan.id,
        task_id=updated_plan.task_id,
        plan_content=json.loads(updated_plan.plan_content),
        version=updated_plan.version,
        status=PlanStatusEnum(updated_plan.status.value),
        created_at=updated_plan.created_at,
        confirmed_at=updated_plan.confirmed_at,
    )
