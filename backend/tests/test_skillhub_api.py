from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_skillhub_search_success():
    with patch("app.api.skill.skill_service.search_skillhub", new=AsyncMock(return_value=[{"name": "weather", "version": "1.0.0"}])):
        response = client.get("/api/v1/agent-center/skills/hub/search", params={"name": "weather"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"][0]["name"] == "weather"


def test_skillhub_install_validation_error():
    response = client.post("/api/v1/agent-center/skills/install", json={"version": "1.0.0"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 400


def test_skillhub_install_success():
    mocked_result = {"task_id": "task-1", "skill_name": "weather", "status": "success"}
    with patch("app.api.skill.skill_service.install_from_hub", new=AsyncMock(return_value=mocked_result)):
        response = client.post("/api/v1/agent-center/skills/install", json={"name": "weather", "version": "1.0.0"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["task_id"] == "task-1"


def test_skillhub_install_failure():
    with patch("app.api.skill.skill_service.install_from_hub", new=AsyncMock(side_effect=ValueError("install failed"))):
        response = client.post("/api/v1/agent-center/skills/install", json={"name": "weather"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 400
    assert "install failed" in body["msg"]
