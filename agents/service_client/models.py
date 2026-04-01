from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ServiceErrorPayload(BaseModel):
    code: str
    message: str
    trace_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class BackendServiceError(Exception):
    def __init__(self, status_code: int, payload: ServiceErrorPayload):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"{status_code} {payload.code}: {payload.message}")


class BackendChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class BackendCompletionRequest(BaseModel):
    messages: List[BackendChatMessage]
    model_name: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    idempotency_key: Optional[str] = None
    timeout_ms: int = 10000


class BackendCompletionResponse(BaseModel):
    content: str
    model_name: str
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BackendVectorSearchRequest(BaseModel):
    query: str
    limit: int = 5
    timeout_ms: int = 10000


class BackendVectorSearchResponse(BaseModel):
    count: int
    articles: List[Dict[str, Any]]
    summary: str
    trace_id: Optional[str] = None
