import os
import time

import httpx


def _wait_until_ready(client: httpx.Client, url: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            response = client.get(url)
            if response.status_code < 500:
                return
            last_error = f"status={response.status_code}"
        except httpx.HTTPError as exc:
            last_error = str(exc)
        time.sleep(1)
    raise AssertionError(f"service not ready: {url}, last_error={last_error}")


def test_agent_center_ci_integration():
    backend_base = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    frontend_base = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:3000")
    required_fields = {"id", "name", "description", "version", "enabled", "createdAt", "updatedAt"}

    with httpx.Client(timeout=10.0) as client:
        _wait_until_ready(client, f"{frontend_base}/frontend/health")
        _wait_until_ready(client, f"{backend_base}/api/v1/agent-center/agents")
        frontend_health = client.get(f"{frontend_base}/frontend/health")
        assert frontend_health.status_code == 200
        assert frontend_health.json().get("status") == "ok"

        agents_resp = client.get(f"{backend_base}/api/v1/agent-center/agents")
        skills_resp = client.get(f"{backend_base}/api/v1/agent-center/skills")

    assert agents_resp.status_code == 200
    assert skills_resp.status_code == 200

    agents_body = agents_resp.json()
    skills_body = skills_resp.json()
    assert agents_body.get("code") == 0
    assert skills_body.get("code") == 0
    assert isinstance(agents_body.get("data"), list)
    assert isinstance(skills_body.get("data"), list)
    assert len(agents_body["data"]) > 0
    assert len(skills_body["data"]) > 0
    assert required_fields.issubset(set(agents_body["data"][0].keys()))
    assert required_fields.issubset(set(skills_body["data"][0].keys()))
