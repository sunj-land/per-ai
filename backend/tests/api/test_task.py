import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.task import Task, TaskLog
import uuid
from unittest.mock import patch, AsyncMock

@patch("app.api.task.task_service.create_task", new_callable=AsyncMock)
def test_create_task(mock_create, client: TestClient):
    mock_create.return_value = Task(
        name="Test Task",
        type="shell",
        payload="echo 'hello'",
        schedule_type="interval",
        schedule_config={"minutes": 5}
    )
    
    response = client.post(
        "/api/v1/tasks/tasks",
        json={
            "name": "Test Task",
            "type": "shell",
            "payload": "echo 'hello'",
            "schedule_type": "interval",
            "schedule_config": {"minutes": 5}
        }
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Task"

def test_get_tasks(client: TestClient, session: Session):
    task = Task(name="T1", type="shell", payload="ls", schedule_type="none")
    session.add(task)
    session.commit()

    response = client.get("/api/v1/tasks/tasks")
    assert response.status_code == 200
    assert len(response.json()) >= 1

@patch("app.api.task.task_service.update_task", new_callable=AsyncMock)
def test_update_task(mock_update, client: TestClient):
    t_id = uuid.uuid4()
    mock_update.return_value = Task(id=t_id, name="Updated", type="shell", payload="ls", schedule_type="none")

    response = client.put(f"/api/v1/tasks/tasks/{str(t_id)}", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"

@patch("app.api.task.task_service.update_task", new_callable=AsyncMock)
def test_update_task_not_found(mock_update, client: TestClient):
    mock_update.return_value = None
    response = client.put(f"/api/v1/tasks/tasks/{str(uuid.uuid4())}", json={"name": "Updated"})
    assert response.status_code == 404

@patch("app.api.task.task_service.delete_task", new_callable=AsyncMock)
def test_delete_task(mock_delete, client: TestClient):
    mock_delete.return_value = True
    response = client.delete(f"/api/v1/tasks/tasks/{str(uuid.uuid4())}")
    assert response.status_code == 200

@patch("app.api.task.task_service.delete_task", new_callable=AsyncMock)
def test_delete_task_not_found(mock_delete, client: TestClient):
    mock_delete.return_value = False
    response = client.delete(f"/api/v1/tasks/tasks/{str(uuid.uuid4())}")
    assert response.status_code == 404

def test_run_task(client: TestClient, session: Session):
    task = Task(name="Run Me", type="shell", payload="pwd", schedule_type="none")
    session.add(task)
    session.commit()
    session.refresh(task)

    # We need to inject the test session into the endpoint because it uses a new session inside
    # Since we can't easily mock the internal session context manager directly, let's mock the DB query
    with patch("app.api.task.Session") as mock_session:
        mock_db = mock_session.return_value.__enter__.return_value
        mock_db.get.return_value = task
        
        with patch("fastapi.BackgroundTasks.add_task") as mock_bg:
            response = client.post(f"/api/v1/tasks/tasks/{str(task.id)}/run")
            assert response.status_code == 200
            mock_bg.assert_called_once()

def test_run_task_not_found(client: TestClient):
    response = client.post(f"/api/v1/tasks/tasks/{str(uuid.uuid4())}/run")
    assert response.status_code == 404

@patch("app.api.task.task_service.pause_task", new_callable=AsyncMock)
def test_pause_task(mock_pause, client: TestClient):
    t_id = uuid.uuid4()
    mock_pause.return_value = Task(id=t_id, name="T", type="shell", payload="ls", schedule_type="none", is_active=False)
    
    response = client.post(f"/api/v1/tasks/tasks/{str(t_id)}/pause")
    assert response.status_code == 200
    assert response.json()["is_active"] is False

@patch("app.api.task.task_service.resume_task", new_callable=AsyncMock)
def test_resume_task(mock_resume, client: TestClient):
    t_id = uuid.uuid4()
    mock_resume.return_value = Task(id=t_id, name="T", type="shell", payload="ls", schedule_type="none", is_active=True)
    
    response = client.post(f"/api/v1/tasks/tasks/{str(t_id)}/resume")
    assert response.status_code == 200
    assert response.json()["is_active"] is True

def test_get_task_logs(client: TestClient, session: Session):
    task = Task(name="Log Task", type="shell", payload="pwd", schedule_type="none")
    session.add(task)
    session.commit()
    session.refresh(task)

    log = TaskLog(task_id=task.id, status="success", output="ok")
    session.add(log)
    session.commit()
    
    # Similarly, mock the Session context manager for this endpoint
    with patch("app.api.task.Session") as mock_session:
        mock_db = mock_session.return_value.__enter__.return_value
        mock_db.exec.return_value.all.return_value = [{"status": "success"}]

        response = client.get(f"/api/v1/tasks/tasks/{str(task.id)}/logs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["status"] == "success"
