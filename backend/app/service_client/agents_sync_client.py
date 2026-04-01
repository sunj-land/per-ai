import os
import logging
import uuid
import httpx
import time
from typing import Generator, Dict, Optional, List, Any
from app.service_client.models import (
    ChatCompletionRequestContract,
    EmbeddingRequestContract,
    TextGenerateRequestContract,
    TextClassifyRequestContract,
    TextSummarizeRequestContract,
    NodeResultContract,
    AgentInfoContract,
    AgentGraphContract,
    AgentsServiceError,
    ServiceErrorPayload
)

try:
    from opentelemetry import trace
except ImportError:
    trace = None

logger = logging.getLogger(__name__)

class _SimpleCircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_seconds: int):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"

    def allow(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_seconds:
                self.state = "HALF_OPEN"
                return True
            return False
        return True

    def success(self):
        self.failures = 0
        self.state = "CLOSED"

    def failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"

class _FixedWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = 0
        self.start_time = time.time()

    def acquire(self):
        if time.time() - self.start_time > self.window_seconds:
            self.start_time = time.time()
            self.requests = 0
        self.requests += 1

class AgentsServiceSyncClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("AGENTS_BASE_URL", "http://localhost:8000")
        self.api_version = os.getenv("INTERNAL_API_VERSION", "v1")
        self.token = os.getenv("SERVICE_JWT_TOKEN", "default-insecure-key")
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
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    def chat_completion_stream(self, payload: ChatCompletionRequestContract) -> Generator[str, None, None]:
        # Force stream=True in payload
        payload.stream = True

        if not self.breaker.allow():
             yield "Error: Service Unavailable (Circuit Open)"
             return

        self.rate_limiter.acquire()

        headers = self._build_headers()

        try:
            with self.client.stream("POST", "/api/v1/chat/completions", json=payload.model_dump(mode="json"), headers=headers) as response:
                if response.status_code != 200:
                    self.breaker.failure()
                    # Read response content for error details
                    response.read()
                    # Try to read error details
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", {}).get("message", response.text)
                    except:
                        error_msg = response.text
                    yield f"Error: {response.status_code} {error_msg}"
                    return

                self.breaker.success()

                for line in response.iter_lines():
                    if line:
                        yield line
        except httpx.RequestError as e:
            self.breaker.failure()
            yield f"Error: Connection failed ({str(e)})"

    def chat_completion(self, payload: ChatCompletionRequestContract) -> Dict:
        response = self._request("POST", "/api/v1/llm/chat", json=payload.model_dump(mode="json"))
        return response.json()

    def embedding(self, payload: EmbeddingRequestContract) -> Dict:
        response = self._request("POST", "/api/v1/llm/embedding", json=payload.model_dump(mode="json"))
        return response.json()

    def text_generate(self, payload: TextGenerateRequestContract) -> NodeResultContract:
        response = self._request("POST", "/api/v1/nodes/generate", json=payload.model_dump(mode="json"))
        return NodeResultContract.model_validate(response.json())

    def text_classify(self, payload: TextClassifyRequestContract) -> NodeResultContract:
        response = self._request("POST", "/api/v1/nodes/classify", json=payload.model_dump(mode="json"))
        return NodeResultContract.model_validate(response.json())

    def text_summarize(self, payload: TextSummarizeRequestContract) -> NodeResultContract:
        response = self._request("POST", "/api/v1/nodes/summarize", json=payload.model_dump(mode="json"))
        return NodeResultContract.model_validate(response.json())

    def list_agents(self) -> List[AgentInfoContract]:
        response = self._request("GET", "/api/v1/agents/list")
        return [AgentInfoContract.model_validate(item) for item in response.json()]

    def get_agent_graph(self, agent_name: str) -> AgentGraphContract:
        response = self._request("GET", f"/api/v1/agents/{agent_name}/graph")
        return AgentGraphContract.model_validate(response.json())

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-API-Key": self.token,
            "X-API-Version": self.api_version,
            "X-Request-Id": str(uuid.uuid4()),
        }
        traceparent = self._traceparent()
        if traceparent:
            headers["traceparent"] = traceparent
        return headers

    def _request(
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

        headers = self._build_headers()
        if timeout_ms:
            headers["X-Timeout-Ms"] = str(timeout_ms)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        last_error: Optional[Exception] = None
        for _ in range(self.max_retries + 1):
            try:
                response = self.client.request(
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
                return response
            except AgentsServiceError:
                self.breaker.failure()
                raise
            except Exception as exc:
                last_error = exc
                self.breaker.failure()
                logger.warning("agents_call_retry method=%s path=%s error=%s", method, path, exc)
                time.sleep(0.2)

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
        try:
            span = trace.get_current_span()
            span_context = span.get_span_context()
            if not span_context or not span_context.is_valid:
                return None
            trace_id = format(span_context.trace_id, "032x")
            span_id = format(span_context.span_id, "016x")
            return f"00-{trace_id}-{span_id}-01"
        except Exception:
            return None
