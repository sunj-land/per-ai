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
    """
    简单的断路器实现，用于保护服务调用。

    工作原理（三状态机）：
    - CLOSED（关闭）：正常请求，允许通过。失败计数达到阈值后切换到 OPEN。
    - OPEN（打开）：服务不可用，直接拒绝请求。经过恢复时间后切换到 HALF_OPEN。
    - HALF_OPEN（半开）：允许一个测试请求。如果成功则回到 CLOSED，失败则回到 OPEN。

    适用场景：防止级联故障，当下游服务持续失败时快速失败，避免资源耗尽。
    """

    def __init__(self, failure_threshold: int, recovery_seconds: int):
        """
        初始化断路器。

        :param failure_threshold: 失败次数阈值，达到此值则打开断路器
        :param recovery_seconds: 恢复等待秒数，断路器打开后等待此时间才允许测试请求
        """
        self.failure_threshold = failure_threshold  # 触发断路的连续失败次数
        self.recovery_seconds = recovery_seconds    # 断路后的恢复等待时间（秒）
        self.failures = 0                           # 当前连续失败计数
        self.last_failure_time = 0                  # 上次失败时间戳（用于计算恢复等待）
        self.state = "CLOSED"                       # 当前状态：CLOSED | OPEN | HALF_OPEN

    def allow(self) -> bool:
        """
        检查是否允许请求通过。

        :return: True 表示允许请求，False 表示拒绝
        """
        # ========== 状态检查逻辑 ==========
        if self.state == "OPEN":
            # 断路器打开中，检查是否超过恢复时间
            if time.time() - self.last_failure_time > self.recovery_seconds:
                # 超过恢复时间，切换到半开状态，允许一个测试请求
                self.state = "HALF_OPEN"
                return True
            return False  # 未超过恢复时间，继续拒绝请求
        return True  # CLOSED 或 HALF_OPEN 状态，允许请求

    def success(self):
        """
        记录成功调用，重置失败计数，关闭断路器。
        """
        self.failures = 0       # 重置失败计数
        self.state = "CLOSED"   # 回到关闭状态

    def failure(self):
        """
        记录失败调用，增加失败计数，判断是否需要打开断路器。
        """
        self.failures += 1                      # 失败计数 +1
        self.last_failure_time = time.time()    # 记录失败时间
        # ========== 判断是否打开断路器 ==========
        if self.failures >= self.failure_threshold:
            # 连续失败达到阈值，打开断路器
            self.state = "OPEN"


class _FixedWindowRateLimiter:
    """
    固定窗口限流器，用于控制请求速率。

    工作原理：固定时间窗口内（如 1 秒）最多允许 N 个请求。窗口到期后重置计数器。
    优点：实现简单，内存占用低
    缺点：窗口边界可能出现流量突刺
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        初始化限流器。

        :param max_requests: 时间窗口内允许的最大请求数
        :param window_seconds: 时间窗口大小（秒）
        """
        self.max_requests = max_requests      # 窗口内最大请求数
        self.window_seconds = window_seconds  # 窗口大小（秒）
        self.requests = 0                   # 当前窗口内已处理的请求数
        self.start_time = time.time()        # 当前窗口开始时间

    def acquire(self):
        """
        获取一个请求配额（消耗一个限流名额）。

        如果当前窗口已满，请求仍会被处理（此实现为宽松限流）。
        严格限流需要在请求被处理前检查并拒绝超限请求。
        """
        # ========== 窗口重置检查 ==========
        if time.time() - self.start_time > self.window_seconds:
            # 窗口到期，重置计数器，开始新窗口
            self.start_time = time.time()
            self.requests = 0
        self.requests += 1  # 当前窗口请求计数 +1


class AgentsServiceSyncClient:
    """
    Agents 服务的同步 HTTP 客户端。

    核心功能：
    - 提供 chat_completion、embedding、text_generate 等 AI 能力接口
    - 内置断路器机制，防止下游服务故障影响上游系统
    - 内置限流器，控制对下游服务的请求速率
    - 支持分布式追踪（OpenTelemetry traceparent）
    - 支持流式响应（SSE/Server-Sent Events）

    使用单例模式，整个应用生命周期复用同一个 HTTP 客户端实例。
    """

    def __init__(self) -> None:
        """
        初始化 Agents 服务同步客户端。

        配置项（环境变量）：
        - AGENTS_BASE_URL: Agents 服务地址，默认 http://localhost:8000
        - INTERNAL_API_VERSION: API 版本，默认 v1
        - SERVICE_JWT_TOKEN: 服务间认证 Token
        - AGENTS_CLIENT_TIMEOUT_SECONDS: 请求超时秒数，默认 60
        - AGENTS_CLIENT_RETRIES: 最大重试次数，默认 1
        - AGENTS_CLIENT_CB_THRESHOLD: 断路器失败阈值，默认 5
        - AGENTS_CLIENT_CB_RECOVERY_SECONDS: 断路器恢复等待秒数，默认 30
        - AGENTS_CLIENT_RATE_LIMIT: 限流器最大 QPS，默认 200
        """
        # ========== 服务配置 ==========
        self.base_url = os.getenv("AGENTS_BASE_URL", "http://localhost:8000")         # 服务基础 URL
        self.api_version = os.getenv("INTERNAL_API_VERSION", "v1")                        # API 版本
        self.token = os.getenv("SERVICE_JWT_TOKEN", "default-insecure-key")             # 认证 Token
        self.timeout = float(os.getenv("AGENTS_CLIENT_TIMEOUT_SECONDS", "60"))           # 请求超时（秒）
        self.max_retries = int(os.getenv("AGENTS_CLIENT_RETRIES", "1"))                  # 最大重试次数

        # ========== 断路器配置 ==========
        self.breaker = _SimpleCircuitBreaker(
            failure_threshold=int(os.getenv("AGENTS_CLIENT_CB_THRESHOLD", "5")),          # 连续失败 5 次则打开断路
            recovery_seconds=int(os.getenv("AGENTS_CLIENT_CB_RECOVERY_SECONDS", "30")), # 等待 30 秒后尝试恢复
        )

        # ========== 限流器配置 ==========
        self.rate_limiter = _FixedWindowRateLimiter(
            max_requests=int(os.getenv("AGENTS_CLIENT_RATE_LIMIT", "200")),              # 每秒最多 200 请求
            window_seconds=1,                                                            # 1 秒时间窗口
        )

        # ========== HTTP 客户端初始化 ==========
        self.client = httpx.Client(
            base_url=self.base_url,                               # 请求基础 URL
            timeout=httpx.Timeout(self.timeout),                 # 全局超时配置
            limits=httpx.Limits(
                max_connections=100,                             # 最多 100 个并发连接
                max_keepalive_connections=20,                    # 最多保持 20 个持久连接
            ),
        )

    def chat_completion_stream(self, payload: ChatCompletionRequestContract) -> Generator[str, None, None]:
        """
        流式聊天补全请求（SSE 响应）。

        :param payload: 聊天补全请求参数
        :return: 生成器，逐行产出服务器返回的事件行
        """
        # ========== 步骤1：强制开启流式响应 ==========
        payload.stream = True

        # ========== 步骤2：断路器检查 ==========
        if not self.breaker.allow():
            # 断路器打开，直接返回错误，不发送请求
            yield "Error: Service Unavailable (Circuit Open)"
            return

        # ========== 步骤3：限流检查 ==========
        self.rate_limiter.acquire()

        # ========== 步骤4：构建请求头 ==========
        headers = self._build_headers()

        try:
            # ========== 步骤5：发送流式请求 ==========
            with self.client.stream(
                "POST",
                "/api/v1/chat/completions",
                json=payload.model_dump(mode="json"),
                headers=headers
            ) as response:
                # ========== 步骤6：处理非 200 响应 ==========
                if response.status_code != 200:
                    self.breaker.failure()  # 记录失败
                    response.read()  # 读取响应体以获取错误详情
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", {}).get("message", response.text)
                    except:
                        error_msg = response.text
                    yield f"Error: {response.status_code} {error_msg}"
                    return

                # ========== 步骤7：请求成功 ==========
                self.breaker.success()  # 重置失败计数

                # ========== 步骤8：流式迭代响应行 ==========
                for line in response.iter_lines():
                    if line:
                        yield line  # 逐行 yield 给调用方

        except httpx.RequestError as e:
            # ========== 步骤9：网络错误处理 ==========
            self.breaker.failure()  # 记录失败
            yield f"Error: Connection failed ({str(e)})"

    def chat_completion(self, payload: ChatCompletionRequestContract) -> Dict:
        """
        非流式聊天补全请求。

        :param payload: 聊天补全请求参数
        :return: 服务器返回的 JSON 响应
        """
        response = self._request("POST", "/api/v1/llm/chat", json=payload.model_dump(mode="json"))
        return response.json()

    def embedding(self, payload: EmbeddingRequestContract) -> Dict:
        """
        文本嵌入向量生成。

        :param payload: 嵌入请求参数
        :return: 包含向量结果的字典
        """
        response = self._request("POST", "/api/v1/llm/embedding", json=payload.model_dump(mode="json"))
        return response.json()

    def text_generate(self, payload: TextGenerateRequestContract) -> NodeResultContract:
        """
        文本生成节点调用。

        :param payload: 生成请求参数
        :return: NodeResultContract 结构化响应
        """
        response = self._request("POST", "/api/v1/nodes/generate", json=payload.model_dump(mode="json"))
        return NodeResultContract.model_validate(response.json())

    def text_classify(self, payload: TextClassifyRequestContract) -> NodeResultContract:
        """
        文本分类节点调用。

        :param payload: 分类请求参数
        :return: NodeResultContract 结构化响应
        """
        response = self._request("POST", "/api/v1/nodes/classify", json=payload.model_dump(mode="json"))
        return NodeResultContract.model_validate(response.json())

    def text_summarize(self, payload: TextSummarizeRequestContract) -> NodeResultContract:
        """
        文本摘要节点调用。

        :param payload: 摘要请求参数
        :return: NodeResultContract 结构化响应
        """
        response = self._request("POST", "/api/v1/nodes/summarize", json=payload.model_dump(mode="json"))
        return NodeResultContract.model_validate(response.json())

    def list_agents(self) -> List[AgentInfoContract]:
        """
        获取可用智能体列表。

        :return: AgentInfoContract 对象列表
        """
        response = self._request("GET", "/api/v1/agents/list")
        return [AgentInfoContract.model_validate(item) for item in response.json()]

    def get_agent_graph(self, agent_name: str) -> AgentGraphContract:
        """
        获取指定智能体的图结构定义。

        :param agent_name: 智能体名称
        :return: AgentGraphContract 结构化响应
        """
        response = self._request("GET", f"/api/v1/agents/{agent_name}/graph")
        return AgentGraphContract.model_validate(response.json())

    def _build_headers(self) -> Dict[str, str]:
        """
        构建请求头，包含认证信息和追踪上下文。

        :return: 请求头字典
        """
        headers = {
            "Authorization": f"Bearer {self.token}",   # Bearer Token 认证
            "X-API-Key": self.token,                    # API Key 认证
            "X-API-Version": self.api_version,          # API 版本
            "X-Request-Id": str(uuid.uuid4()),           # 请求唯一 ID（用于日志追踪）
        }
        # ========== 添加分布式追踪头 ==========
        traceparent = self._traceparent()
        if traceparent:
            headers["traceparent"] = traceparent  # W3C Trace Context 标准格式
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
        """
        通用 HTTP 请求方法，内置断路器、限流、重试和错误处理。

        :param method: HTTP 方法（GET/POST/PUT/DELETE 等）
        :param path: 请求路径（相对于 base_url）
        :param params: URL 查询参数
        :param json: JSON 请求体
        :param timeout_ms: 单次请求超时（毫秒）
        :param idempotency_key: 幂等键（用于防止重复提交）
        :return: httpx.Response 响应对象
        :raises AgentsServiceError: 服务错误时抛出
        """
        # ========== 步骤1：断路器检查 ==========
        if not self.breaker.allow():
            raise AgentsServiceError(
                status_code=503,
                payload=ServiceErrorPayload(
                    code="CIRCUIT_OPEN",
                    message="agents client circuit is open"
                ),
            )

        # ========== 步骤2：限流检查 ==========
        self.rate_limiter.acquire()

        # ========== 步骤3：构建请求头 ==========
        headers = self._build_headers()
        if timeout_ms:
            headers["X-Timeout-Ms"] = str(timeout_ms)  # 添加超时配置
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key  # 添加幂等键

        # ========== 步骤4：发送请求（带重试） ==========
        last_error: Optional[Exception] = None
        for _ in range(self.max_retries + 1):  # max_retries + 1 次尝试
            try:
                response = self.client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                    headers=headers,
                )

                # ========== 步骤5：状态码处理 ==========
                if response.status_code >= 500:
                    # 服务器错误，触发重试
                    raise httpx.HTTPStatusError(
                        message="upstream server error",
                        request=response.request,
                        response=response,
                    )
                if response.status_code >= 400:
                    # 客户端错误（4xx），不重试，直接抛出
                    payload = self._parse_error_payload(response)
                    raise AgentsServiceError(response.status_code, payload)

                # ========== 步骤6：成功响应 ==========
                self.breaker.success()  # 重置失败计数
                return response

            except AgentsServiceError:
                # 已知业务错误，不重试，直接上抛
                self.breaker.failure()
                raise
            except Exception as exc:
                # 其他异常（如网络错误），记录日志并重试
                last_error = exc
                self.breaker.failure()
                logger.warning(
                    "agents_call_retry method=%s path=%s error=%s",
                    method, path, exc
                )
                time.sleep(0.2)  # 重试前等待 200ms

        # ========== 步骤7：重试耗尽，抛出最终错误 ==========
        raise AgentsServiceError(
            status_code=503,
            payload=ServiceErrorPayload(
                code="UPSTREAM_UNAVAILABLE",
                message=str(last_error) if last_error else "agents unavailable",
            ),
        )

    def _parse_error_payload(self, response: httpx.Response) -> ServiceErrorPayload:
        """
        解析错误响应体，提取结构化的错误信息。

        支持多种错误格式：
        - {"error": {...}}
        - {"detail": {"error": {...}}}
        - {"detail": "error message"}

        :param response: HTTP 响应对象
        :return: ServiceErrorPayload 结构化错误
        """
        try:
            data = response.json()
            # 格式1：{"error": {"code": "...", "message": "..."}}
            if isinstance(data, dict) and "error" in data and isinstance(data["error"], dict):
                return ServiceErrorPayload.model_validate(data["error"])

            # 格式2：{"detail": {"error": {...}}}
            if isinstance(data, dict) and "detail" in data:
                detail = data["detail"]
                if isinstance(detail, dict) and "error" in detail and isinstance(detail["error"], dict):
                    return ServiceErrorPayload.model_validate(detail["error"])
                # 格式3：{"detail": {"message": "..."}}
                if isinstance(detail, dict):
                    return ServiceErrorPayload(
                        code="UPSTREAM_ERROR",
                        message=detail.get("message", str(detail))
                    )
                # 格式4：{"detail": "error string"}
                return ServiceErrorPayload(code="UPSTREAM_ERROR", message=str(detail))
        except Exception:
            pass
        # 解析失败，返回原始响应文本
        return ServiceErrorPayload(
            code="UPSTREAM_ERROR",
            message=response.text or "request failed"
        )

    def _traceparent(self) -> Optional[str]:
        """
        获取当前上下文的 W3C Trace Context traceparent 头。

        用于分布式追踪，将请求链路从 Backend 传递到 Agents 服务。
        格式：00-{trace_id}-{span_id}-01

        :return: traceparent 字符串，如果无法获取则返回 None
        """
        # ========== 检查 OpenTelemetry 是否可用 ==========
        if trace is None:
            return None
        try:
            # 获取当前活跃的 Span
            span = trace.get_current_span()
            span_context = span.get_span_context()
            # 检查 span 上下文是否有效
            if not span_context or not span_context.is_valid:
                return None
            # 格式化为 W3C Trace Context 标准格式
            trace_id = format(span_context.trace_id, "032x")  # 32 位十六进制
            span_id = format(span_context.span_id, "016x")    # 16 位十六进制
            return f"00-{trace_id}-{span_id}-01"             # 版本-TraceID-SpanID-采样标志
        except Exception:
            return None
