import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import app_config

Base = declarative_base()


def utcnow():
    """返回当前UTC时间"""
    return datetime.now(timezone.utc)


class TaskStatus(str, enum.Enum):
    planning = "planning"
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class PlanStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    modified = "modified"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    topic = Column(String(500), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.planning, nullable=False)
    depth = Column(String(20), default="standard")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    plan = relationship("ResearchPlan", back_populates="task", uselist=False, cascade="all, delete-orphan")
    results = relationship("TaskResult", back_populates="task", uselist=False, cascade="all, delete-orphan")
    logs = relationship("ExecutionLog", back_populates="task", cascade="all, delete-orphan")


class ResearchPlan(Base):
    __tablename__ = "research_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("tasks.task_id"), nullable=False, index=True)
    plan_content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(Enum(PlanStatus), default=PlanStatus.draft, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)

    task = relationship("Task", back_populates="plan")


class TaskResult(Base):
    __tablename__ = "task_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("tasks.task_id"), nullable=False, index=True)
    report_content = Column(Text, nullable=True)
    report_format = Column(String(20), default="markdown")
    sources_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    task = relationship("Task", back_populates="results")


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("tasks.task_id"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=True)
    step_name = Column(String(200), nullable=True)
    log_level = Column(String(20), default="info")
    message = Column(Text, nullable=True)
    validation_event = Column(Integer, default=0)
    timestamp = Column(DateTime, default=utcnow, nullable=False)

    task = relationship("Task", back_populates="logs")


engine = create_engine(
    app_config.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in app_config.database_url else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
