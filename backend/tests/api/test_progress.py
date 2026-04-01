import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.user import User
from app.models.progress import UserProgress, EventLog, EventType

def test_get_progress(authenticated_client: TestClient):
    response = authenticated_client.get("/api/v1/progress/")
    assert response.status_code == 200
    assert "total_study_time_min" in response.json()

def test_log_event(authenticated_client: TestClient, session: Session, mock_user: User):
    response = authenticated_client.post(
        "/api/v1/progress/events",
        json={"event_type": "finish", "duration_sec": 120, "user_id": 1, "article_id": 1}
    )
    assert response.status_code == 200

    # check progress updated
    p = session.query(UserProgress).filter_by(user_id=mock_user.id).first()
    assert p.total_study_time_min >= 2.0

def test_list_events(authenticated_client: TestClient, session: Session, mock_user: User):
    e = EventLog(user_id=mock_user.id, event_type="start_learn", duration_sec=0, article_id=1)
    session.add(e)
    session.commit()

    response = authenticated_client.get("/api/v1/progress/events")
    assert response.status_code == 200
    assert len(response.json()) >= 1
