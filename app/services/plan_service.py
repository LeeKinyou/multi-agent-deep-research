import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.database import PlanStatus, ResearchPlan, TaskStatus
from app.models.schemas import PlanConfirmRequest, PlanStatusEnum

logger = logging.getLogger(__name__)


class PlanService:
    def __init__(self, db: Session):
        self.db = db

    def create_plan(self, task_id: str, plan_content: Dict[str, Any], version: int = 1) -> ResearchPlan:
        plan_json = json.dumps(plan_content, ensure_ascii=False)
        plan = ResearchPlan(
            task_id=task_id,
            plan_content=plan_json,
            version=version,
            status=PlanStatus.draft,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        logger.info(f"Plan created for task {task_id}, version {version}")
        return plan

    def get_plan(self, task_id: str) -> Optional[ResearchPlan]:
        return self.db.query(ResearchPlan).filter(ResearchPlan.task_id == task_id).first()

    def confirm_plan(self, task_id: str, request: PlanConfirmRequest) -> Optional[ResearchPlan]:
        plan = self.get_plan(task_id)
        if not plan:
            logger.warning(f"Plan not found for task {task_id}")
            return None

        if request.confirmed:
            plan.status = PlanStatus.confirmed
            plan.confirmed_at = datetime.utcnow()
            logger.info(f"Plan confirmed for task {task_id}")
        else:
            plan.status = PlanStatus.modified
            logger.info(f"Plan modification requested for task {task_id}: {request.modifications}")

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def update_plan(self, task_id: str, plan_content: Dict[str, Any]) -> Optional[ResearchPlan]:
        plan = self.get_plan(task_id)
        if not plan:
            logger.warning(f"Plan not found for task {task_id}")
            return None

        plan.plan_content = json.dumps(plan_content, ensure_ascii=False)
        plan.version += 1
        plan.status = PlanStatus.draft
        plan.confirmed_at = None

        self.db.commit()
        self.db.refresh(plan)
        logger.info(f"Plan updated for task {task_id}, new version {plan.version}")
        return plan

    def get_plan_dict(self, plan: ResearchPlan) -> Dict[str, Any]:
        try:
            return json.loads(plan.plan_content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse plan content for task {plan.task_id}")
            return {}
