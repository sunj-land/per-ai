import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.user import User
from app.models.reminder import UserReminder

def test_list_reminders(authenticated_client: TestClient, session: Session, mock_user: User):
    r = UserReminder(user_id=mock_user.id, cron_expression="0 9 * * *", method="email")
    session.add(r)
    session.commit()

    response = authenticated_client.get("/api/v1/reminders/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["method"] == "email"

def test_create_reminder(authenticated_client: TestClient):
    response = authenticated_client.post(
        "/api/v1/reminders/",
        json={"user_id": 1, "cron_expression": "0 10 * * *", "method": "webhook", "target_url": "http://a.com"}
    )
    assert response.status_code == 200
    assert response.json()["method"] == "webhook"

def test_delete_reminder(authenticated_client: TestClient, session: Session, mock_user: User):
    r = UserReminder(user_id=mock_user.id, method="email")
    session.add(r)
    session.commit()
    session.refresh(r)

    response = authenticated_client.delete(f"/api/v1/reminders/{r.reminder_id}")
    assert response.status_code == 200
    assert session.get(UserReminder, r.reminder_id) is None

def test_delete_reminder_not_found(authenticated_client: TestClient):
    response = authenticated_client.delete("/api/v1/reminders/9999")
    assert response.status_code == 404
