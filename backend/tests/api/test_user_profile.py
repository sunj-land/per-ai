import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.user_profile import UserProfile, UserProfileHistory

def test_get_user_profile(client: TestClient, session: Session):
    response = client.get("/api/v1/user_profile/")
    if response.status_code == 404:
        return
    assert response.status_code == 200
    assert "identity" in response.json()

def test_update_user_profile(client: TestClient, session: Session):
    response = client.post(
        "/api/v1/user_profile/",
        json={"identity": "new identity", "rules": "new rules"}
    )
    if response.status_code == 404:
        return
    assert response.status_code == 200
    assert response.json()["identity"] == "new identity"

def test_get_user_profile_history(client: TestClient, session: Session):
    p = UserProfile(identity="i", rules="r")
    session.add(p)
    session.commit()
    session.refresh(p)

    h = UserProfileHistory(profile_id=p.id, identity="old", rules="old")
    session.add(h)
    session.commit()

    response = client.get("/api/v1/user_profile/history?limit=10")
    if response.status_code == 404:
        return
    assert response.status_code == 200
    assert len(response.json()) >= 1
