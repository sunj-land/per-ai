import pytest
from fastapi.testclient import TestClient
from app.main import app
import httpx

client = TestClient(app)

def test_proxy_agents_requests_error_handling(monkeypatch):
    """
    Test that the proxy correctly handles a situation where the upstream agents service is unavailable.
    """
    async def mock_send(*args, **kwargs):
        raise httpx.RequestError("Mocked connection error")
        
    monkeypatch.setattr(httpx.AsyncClient, "send", mock_send)
    
    response = client.get("/api/v1/agents/health")
    assert response.status_code == 502
    assert "Bad Gateway" in response.json()["detail"]

def test_proxy_agents_requests_success(monkeypatch):
    """
    Test that the proxy correctly forwards the request and returns the upstream response.
    """
    class MockResponse:
        status_code = 200
        headers = {"content-type": "application/json"}
        async def aiter_raw(self):
            yield b'{"status": "ok"}'
        async def aclose(self):
            pass

    async def mock_send(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "send", mock_send)

    response = client.get("/api/v1/agents/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
