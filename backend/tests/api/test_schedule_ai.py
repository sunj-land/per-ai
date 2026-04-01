import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.models.schedule import Schedule
from datetime import datetime

@patch("app.api.schedule_ai.schedule_service.get_schedules", new_callable=AsyncMock)
def test_search_schedules_ai(mock_get, client: TestClient):
    mock_get.return_value = [
        Schedule(title="Meeting", start_time=datetime.now(), priority=1)
    ]
    
    response = client.post(
        "/api/v1/schedule-ai/search",
        json={"query": "today meeting", "limit": 10}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "today meeting"
    assert "start_time" in data["parsed_time_range"]
    assert len(data["results"]) >= 1
    assert data["results"][0]["title"] == "Meeting"

def test_get_mcp_tools(client: TestClient):
    response = client.get("/api/v1/schedule-ai/mcp/tools")
    assert response.status_code == 200
    assert "tools" in response.json()

def test_call_mcp_tool_not_found(client: TestClient):
    response = client.post(
        "/api/v1/schedule-ai/mcp/call",
        json={"tool_name": "non_existent_tool", "arguments": {}}
    )
    assert response.status_code == 404
