import asyncio
import httpx

from app.service_client.agents_client import AgentsServiceClient
from app.service_client.models import AgentQueryRequestContract


def test_agents_client_query_contract_headers_and_schema():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        return httpx.Response(
            status_code=200,
            json={
                "answer": "ok",
                "source_agent": "master",
                "latency_ms": 12.3,
                "metadata": {"intent": "GENERAL_CHAT"},
                "error": None,
            },
        )

    client = AgentsServiceClient()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://test")

    payload = AgentQueryRequestContract(
        query="hello",
        session_id="sid-1",
        history=[],
        parameters={"timeout_ms": 1000, "idempotency_key": "idem-1"},
    )
    response = asyncio.run(client.query(payload))
    asyncio.run(client.client.aclose())

    assert captured["path"] == "/api/v1/agents/query"
    assert captured["headers"]["x-api-version"] == "v1"
    assert captured["headers"]["authorization"].startswith("Bearer ")
    assert captured["headers"]["idempotency-key"] == "idem-1"
    assert response.answer == "ok"
    assert response.source_agent == "master"
