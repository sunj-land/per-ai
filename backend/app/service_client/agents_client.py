import asyncio
import logging
import os
import threading
import time
import uuid
from typing import Dict, Optional

import httpx
try:
    from opentelemetry import trace
except Exception:
    trace = None

from app.service_client.models import (
    AgentLogUploadRequestContract,
    AgentQueryRequestContract,
    AgentQueryResponseContract,
    AgentsServiceError,
    ServiceErrorPayload,
    ChatCompletionRequestContract,
    EmbeddingRequestContract,
    TextGenerateRequestContract,
    TextClassifyRequestContract,
    TextSummarizeRequestContract,
    NodeResultContract,
)

logger = logging.getLogger(__name__)


class _SimpleCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.opened_at: Optional[float] = None
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self.opened_at is None:
                return True
            if time.time() - self.opened_at >= self.recovery_seconds:
                self.failures = 0
                self.opened_at = None
                return True
            return False

    def success(self) -> None:
        with self._lock:
            self.failures = 0
            self.opened_at = None

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.opened_at = time.time()


class _FixedWindowRateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 1):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._window_start = time.time()
        self._count = 0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.time()
            if now - self._window_start >= self.window_seconds:
                self._window_start = now
                self._count = 0
            if self._count >= self.max_requests:
                raise RuntimeError("rate limit exceeded")
            self._count += 1


class AgentsServiceClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("AGENTS_BASE_URL", "http://localhost:8001")
        self.api_version = os.getenv("INTERNAL_API_VERSION", "v1")
        self.token = os.getenv("SERVICE_JWT_TOKEN", "change-me")
        self.timeout = float(os.getenv("AGENTS_CLIENT_TIMEOUT_SECONDS", "60"))
        self.max_retries = int(os.getenv("AGENTS_CLIENT_RETRIES", "1"))
        self.breaker = _SimpleCircuitBreaker(
            failure_threshold=int(os.getenv("AGENTS_CLIENT_CB_THRESHOLD", "5")),
            recovery_seconds=int(os.getenv("AGENTS_CLIENT_CB_RECOVERY_SECONDS", "30")),
        )
        self.rate_limiter = _FixedWindowRateLimiter(
            max_requests=int(os.getenv("AGENTS_CLIENT_RATE_LIMIT", "200")),
            window_seconds=1,
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    async def query(self, payload: AgentQueryRequestContract) -> AgentQueryResponseContract:
        response = await self._request(
            "POST",
            "/api/v1/agents/query",
            json=payload.model_dump(),
            timeout_ms=payload.parameters.get("timeout_ms"),
            idempotency_key=payload.parameters.get("idempotency_key"),
        )
        return AgentQueryResponseContract.model_validate(response.json())

    async def health(self) -> Dict:
        response = await self._request("GET", "/api/v1/agents/health")
        return response.json()

    async def get_models(self) -> Dict:
        response = await self._request("GET", "/api/v1/models")
        return response.json()

    async def get_models(self) -> Dict:
        response = await self._request("GET", "/api/v1/models")
        return response.json()

    async def upload_logs(self, payload: AgentLogUploadRequestContract) -> Dict:
        response = await self._request("POST", "/api/v1/agents/logs/upload", json=payload.model_dump(mode="json"))
        return response.json()

    async def chat_completion(self, payload: ChatCompletionRequestContract) -> Dict:
        response = await self._request("POST", "/api/v1/chat/completions", json=payload.model_dump(mode="json"))
        return response.json()

    async def embedding(self, payload: EmbeddingRequestContract) -> Dict:
        response = await self._request("POST", "/api/v1/llm/embedding", json=payload.model_dump(mode="json"))
        return response.json()

    async def text_generate(self, payload: TextGenerateRequestContract) -> NodeResultContract:
        response = await self._request("POST", "/api/v1/nodes/generate", json=payload.model_dump(mode="json"))
        return NodeResultContract.model_validate(response.json())

    async def text_classify(self, payload: TextClassifyRequestContract) -> NodeResultContract:
        response = await self._request("POST", "/api/v1/nodes/classify", json=payload.model_dump(mode="json"))
        return NodeResultContract.model_validate(response.json())

    async def text_summarize(self, payload: TextSummarizeRequestContract) -> NodeResultContract:
        response = await self._request("POST", "/api/v1/nodes/summarize", json=payload.model_dump(mode="json"))
        return NodeResultContract.model_validate(response.json())

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, str | int]] = None,
        json: Optional[Dict] = None,
        timeout_ms: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> httpx.Response:
        if not self.breaker.allow():
            raise AgentsServiceError(
                status_code=503,
                payload=ServiceErrorPayload(code="CIRCUIT_OPEN", message="agents client circuit is open"),
            )
        self.rate_limiter.acquire()

        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-API-Key": self.token,
            "X-API-Version": self.api_version,
            "X-Request-Id": str(uuid.uuid4()),
        }
        traceparent = self._traceparent()
        if traceparent:
            headers["traceparent"] = traceparent
        if timeout_ms:
            headers["X-Timeout-Ms"] = str(timeout_ms)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        last_error: Optional[Exception] = None
        for _ in range(self.max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                    headers=headers,
                )
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        message="upstream server error",
                        request=response.request,
                        response=response,
                    )
                if response.status_code >= 400:
                    payload = self._parse_error_payload(response)
                    raise AgentsServiceError(response.status_code, payload)
                self.breaker.success()
                logger.info("agents_call_success method=%s path=%s status=%s", method, path, response.status_code)
                return response
            except AgentsServiceError:
                self.breaker.failure()
                raise
            except Exception as exc:
                last_error = exc
                self.breaker.failure()
                logger.warning("agents_call_retry method=%s path=%s error=%s", method, path, exc)
                await asyncio.sleep(0.2)

        raise AgentsServiceError(
            status_code=503,
            payload=ServiceErrorPayload(
                code="UPSTREAM_UNAVAILABLE",
                message=str(last_error) if last_error else "agents unavailable",
            ),
        )

    def _parse_error_payload(self, response: httpx.Response) -> ServiceErrorPayload:
        try:
            data = response.json()
            if isinstance(data, dict) and "error" in data and isinstance(data["error"], dict):
                return ServiceErrorPayload.model_validate(data["error"])
            if isinstance(data, dict) and "detail" in data:
                detail = data["detail"]
                if isinstance(detail, dict) and "error" in detail and isinstance(detail["error"], dict):
                    return ServiceErrorPayload.model_validate(detail["error"])
                if isinstance(detail, dict):
                    return ServiceErrorPayload(code="UPSTREAM_ERROR", message=detail.get("message", str(detail)))
                return ServiceErrorPayload(code="UPSTREAM_ERROR", message=str(detail))
        except Exception:
            pass
        return ServiceErrorPayload(code="UPSTREAM_ERROR", message=response.text or "request failed")

    def _traceparent(self) -> Optional[str]:
        if trace is None:
            return None
        span = trace.get_current_span()
        span_context = span.get_span_context()
        if not span_context or not span_context.is_valid:
            return None
        trace_id = format(span_context.trace_id, "032x")
        span_id = format(span_context.span_id, "016x")
        return f"00-{trace_id}-{span_id}-01"
