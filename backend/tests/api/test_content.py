import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.content import ContentRepo

def test_create_content(authenticated_client: TestClient, session: Session):
    response = authenticated_client.post(
        "/api/v1/content/",
        json={"task_id": 1, "content_type": "text", "title": "test", "text": "hello"}
    )
    assert response.status_code == 200
    assert response.json()["text"] == "hello"

def test_list_content_by_task(authenticated_client: TestClient, session: Session):
    c = ContentRepo(task_id=2, content_type="text", text="world", title="test")
    session.add(c)
    session.commit()

    response = authenticated_client.get("/api/v1/content/task/2")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["text"] == "world"
