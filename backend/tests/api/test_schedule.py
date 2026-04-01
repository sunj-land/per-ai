import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.schedule import Schedule, ScheduleReminder
import uuid
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

@patch("app.api.schedule.schedule_service.backup_data")
def test_backup_schedules(mock_backup, client: TestClient):
    mock_backup.return_value = {"schedules": [], "reminders": []}
    response = client.get("/api/v1/schedules/backup")
    assert response.status_code == 200
    assert "schedules" in response.json()

@patch("app.api.schedule.schedule_service.restore_data")
def test_restore_schedules(mock_restore, client: TestClient):
    import json
    data = {"schedules": [{"id": str(uuid.uuid4())}]}
    response = client.post(
        "/api/v1/schedules/restore",
        files={"file": ("backup.json", json.dumps(data).encode("utf-8"), "application/json")}
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

@patch("app.api.schedule.schedule_service.create_schedule", new_callable=AsyncMock)
def test_create_schedule(mock_create, client: TestClient):
    mock_create.return_value = Schedule(title="Meeting", start_time=datetime.now())
    response = client.post(
        "/api/v1/schedules",
        json={
            "title": "Meeting",
            "start_time": datetime.now().isoformat(),
            "reminders": []
        }
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Meeting"

@patch("app.api.schedule.schedule_service.get_schedules", new_callable=AsyncMock)
def test_get_schedules(mock_get_all, client: TestClient):
    mock_get_all.return_value = [Schedule(title="Meeting", start_time=datetime.now())]
    response = client.get("/api/v1/schedules")
    assert response.status_code == 200
    assert len(response.json()) >= 1

@patch("app.api.schedule.schedule_service.get_schedule", new_callable=AsyncMock)
def test_get_schedule(mock_get, client: TestClient):
    s_id = uuid.uuid4()
    mock_get.return_value = Schedule(id=s_id, title="Meeting", start_time=datetime.now())
    response = client.get(f"/api/v1/schedules/{str(s_id)}")
    assert response.status_code == 200
    assert response.json()["title"] == "Meeting"

@patch("app.api.schedule.schedule_service.get_schedule", new_callable=AsyncMock)
def test_get_schedule_not_found(mock_get, client: TestClient):
    mock_get.return_value = None
    response = client.get(f"/api/v1/schedules/{str(uuid.uuid4())}")
    assert response.status_code == 404

@patch("app.api.schedule.schedule_service.update_schedule", new_callable=AsyncMock)
def test_update_schedule(mock_update, client: TestClient):
    s_id = uuid.uuid4()
    mock_update.return_value = Schedule(id=s_id, title="Updated", start_time=datetime.now())
    response = client.put(
        f"/api/v1/schedules/{str(s_id)}",
        json={"title": "Updated", "start_time": datetime.now().isoformat()}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"

@patch("app.api.schedule.schedule_service.delete_schedule", new_callable=AsyncMock)
def test_delete_schedule(mock_delete, client: TestClient):
    mock_delete.return_value = True
    response = client.delete(f"/api/v1/schedules/{str(uuid.uuid4())}")
    assert response.status_code == 200

def test_get_schedule_reminders(client: TestClient, session: Session):
    s = Schedule(title="T", start_time=datetime.now())
    session.add(s)
    session.commit()
    session.refresh(s)

    r = ScheduleReminder(schedule_id=s.id, notify_time=datetime.now(), method="dingtalk", remind_at=datetime.now())
    session.add(r)
    session.commit()

    with patch("app.api.schedule.Session") as mock_session:
        mock_db = mock_session.return_value.__enter__.return_value
        mock_db.exec.return_value.all.return_value = [r]

        response = client.get(f"/api/v1/schedules/{str(s.id)}/reminders")
        assert response.status_code == 200
        assert len(response.json()) >= 1
