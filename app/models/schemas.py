from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatusEnum(str, Enum):
    planning = "planning"
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class PlanStatusEnum(str, Enum):
    draft = "draft"
    confirmed = "confirmed"
    modified = "modified"


class TaskCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500, description="研究主题")
    depth: str = Field(default="standard", description="研究深度: standard 或 deep")


class TaskResponse(BaseModel):
    task_id: str
    topic: str
    status: TaskStatusEnum
    depth: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int


class PlanTask(BaseModel):
    task_id: str
    description: str
    agent: str
    search_queries: Optional[List[str]] = None
    expected_output: str


class ResearchPlanCreate(BaseModel):
    task_id: str
    plan_content: Dict[str, Any]
    version: int = 1
    status: PlanStatusEnum = PlanStatusEnum.draft


class ResearchPlanResponse(BaseModel):
    id: int
    task_id: str
    plan_content: Dict[str, Any]
    version: int
    status: PlanStatusEnum
    created_at: datetime
    confirmed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanConfirmRequest(BaseModel):
    confirmed: bool = Field(..., description="是否确认计划")
    modifications: Optional[str] = Field(None, description="修改意见")


class TaskResultResponse(BaseModel):
    task_id: str
    report_content: Optional[str] = None
    report_format: str
    sources_count: int
    word_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutionLogResponse(BaseModel):
    id: int
    task_id: str
    agent_name: Optional[str] = None
    step_name: Optional[str] = None
    log_level: str
    message: Optional[str] = None
    validation_event: bool
    timestamp: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    database: str
