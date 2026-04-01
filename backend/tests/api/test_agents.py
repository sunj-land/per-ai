import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

@patch("httpx.AsyncClient.send")
def test_proxy_agents_requests(mock_send, client: TestClient):
    # Mock httpx response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    
    # Needs to be a real async generator since aciose is awaited
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "application/json"}
            
        async def aiter_raw(self):
            yield b'{"status": "ok"}'
            
        async def aclose(self):
            pass
            
    mock_send.return_value = MockResponse()

    response = client.get("/api/v1/agents/some/path")
    assert response.status_code == 200
    assert "ok" in response.text
