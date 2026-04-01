from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class ServiceErrorPayload(BaseModel):
    code: str
    message: str
    trace_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class AgentsServiceError(Exception):
    def __init__(self, status_code: int, payload: ServiceErrorPayload):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"{status_code} {payload.code}: {payload.message}")


class AgentMessageContract(BaseModel):
    role: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentQueryRequestContract(BaseModel):
    query: str
    session_id: str
    history: List[AgentMessageContract] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentQueryResponseContract(BaseModel):
    answer: str
    source_agent: str
    latency_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class AgentLogUploadRequestContract(BaseModel):
    start_date: str
    end_date: str
    upload_url: HttpUrl
    delete_after_upload: bool = False
    timeout_seconds: int = 30


class ChatCompletionRequestContract(BaseModel):
    messages: List[Dict[str, Any]]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    extra_params: Dict[str, Any] = Field(default_factory=dict)

class EmbeddingRequestContract(BaseModel):
    input: Union[str, List[str]]
    model: Optional[str] = None
    extra_params: Dict[str, Any] = Field(default_factory=dict)

class TextGenerateRequestContract(BaseModel):
    input_text: str
    system_prompt: Optional[str] = "You are a helpful assistant."
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    retries: int = 3

class TextClassifyRequestContract(BaseModel):
    input_text: str
    categories: List[str]
    system_prompt: Optional[str] = None
    model: Optional[str] = None

class TextSummarizeRequestContract(BaseModel):
    input_text: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None

class NodeResultContract(BaseModel):
    result: Any

class AgentInfoContract(BaseModel):
    name: str
    description: str
    type: str = "standard"
    status: str = "active"
    config: Dict[str, Any] = Field(default_factory=dict)

class AgentGraphContract(BaseModel):
    mermaid: str
