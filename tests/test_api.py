import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_health_check():
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "MultiAgentDeepResearch API" in data["message"]


def test_create_task():
    response = client.post(
        "/api/v1/tasks/",
        json={"topic": "人工智能发展趋势", "depth": "standard"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["topic"] == "人工智能发展趋势"
    assert data["status"] == "planning"
    assert "task_id" in data


def test_get_task():
    create_response = client.post(
        "/api/v1/tasks/",
        json={"topic": "测试主题", "depth": "standard"},
    )
    task_id = create_response.json()["task_id"]

    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["topic"] == "测试主题"


def test_get_task_not_found():
    response = client.get("/api/v1/tasks/nonexistent")
    assert response.status_code == 404


def test_list_tasks():
    for i in range(3):
        client.post(
            "/api/v1/tasks/",
            json={"topic": f"主题{i}", "depth": "standard"},
        )

    response = client.get("/api/v1/tasks/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["tasks"]) == 3


def test_create_and_get_plan():
    create_task_response = client.post(
        "/api/v1/tasks/",
        json={"topic": "计划测试", "depth": "standard"},
    )
    task_id = create_task_response.json()["task_id"]

    plan_content = {
        "tasks": [
            {
                "task_id": "1",
                "description": "搜索相关信息",
                "agent": "ResearchAgent",
            }
        ]
    }

    response = client.post(
        f"/api/v1/tasks/{task_id}/plan/",
        json={
            "task_id": task_id,
            "plan_content": plan_content,
            "version": 1,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == task_id
    assert data["version"] == 1
    assert data["status"] == "draft"


def test_get_plan():
    create_task_response = client.post(
        "/api/v1/tasks/",
        json={"topic": "获取计划测试", "depth": "standard"},
    )
    task_id = create_task_response.json()["task_id"]

    plan_content = {"tasks": []}
    client.post(
        f"/api/v1/tasks/{task_id}/plan/",
        json={
            "task_id": task_id,
            "plan_content": plan_content,
        },
    )

    response = client.get(f"/api/v1/tasks/{task_id}/plan/")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id


def test_confirm_plan():
    create_task_response = client.post(
        "/api/v1/tasks/",
        json={"topic": "确认计划测试", "depth": "standard"},
    )
    task_id = create_task_response.json()["task_id"]

    plan_content = {"tasks": []}
    client.post(
        f"/api/v1/tasks/{task_id}/plan/",
        json={
            "task_id": task_id,
            "plan_content": plan_content,
        },
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/plan/confirm",
        json={"confirmed": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"


def test_confirm_plan_not_found():
    response = client.post(
        "/api/v1/tasks/nonexistent/plan/confirm",
        json={"confirmed": True},
    )
    assert response.status_code == 404


def test_cancel_task():
    create_response = client.post(
        "/api/v1/tasks/",
        json={"topic": "取消任务测试", "depth": "standard"},
    )
    task_id = create_response.json()["task_id"]

    response = client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert "cancelled successfully" in data["message"]


def test_get_task_result_not_completed():
    create_response = client.post(
        "/api/v1/tasks/",
        json={"topic": "结果测试", "depth": "standard"},
    )
    task_id = create_response.json()["task_id"]

    response = client.get(f"/api/v1/tasks/{task_id}/result")
    assert response.status_code == 400


def test_get_task_logs():
    create_response = client.post(
        "/api/v1/tasks/",
        json={"topic": "日志测试", "depth": "standard"},
    )
    task_id = create_response.json()["task_id"]

    response = client.get(f"/api/v1/tasks/{task_id}/logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_task_empty_topic():
    response = client.post(
        "/api/v1/tasks/",
        json={"topic": "", "depth": "standard"},
    )
    assert response.status_code == 422


def test_create_task_invalid_depth():
    response = client.post(
        "/api/v1/tasks/",
        json={"topic": "测试", "depth": "invalid"},
    )
    assert response.status_code == 201
