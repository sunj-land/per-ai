import asyncio
import httpx

from service_client.backend_client import BackendServiceClient
from service_client.models import BackendCompletionRequest, BackendChatMessage, BackendVectorSearchRequest


def test_backend_client_completion_contract_headers_and_schema():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        return httpx.Response(
            status_code=200,
            json={
                "content": "hello",
                "model_name": "llama3",
                "trace_id": "trace-1",
                "metadata": {},
            },
        )

    client = BackendServiceClient()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://test")
    payload = BackendCompletionRequest(
        messages=[BackendChatMessage(role="user", content="hi")],
        model_name="llama3",
        idempotency_key="idem-2",
    )
    result = asyncio.run(client.completion(payload))
    asyncio.run(client.client.aclose())

    assert captured["path"] == "/api/v1/internal/chat/completions"
    assert captured["headers"]["x-api-version"] == "v1"
    assert captured["headers"]["authorization"].startswith("Bearer ")
    assert captured["headers"]["idempotency-key"] == "idem-2"
    assert result.content == "hello"


def test_backend_client_vector_search_contract_schema():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json=[{"id": "a1", "content": "doc"}],
            headers={"X-Trace-Id": "trace-2"},
        )

    client = BackendServiceClient()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://test")
    result = asyncio.run(client.search_vectors(BackendVectorSearchRequest(query="k", limit=1)))
    asyncio.run(client.client.aclose())

    assert result.count == 1
    assert result.trace_id == "trace-2"
