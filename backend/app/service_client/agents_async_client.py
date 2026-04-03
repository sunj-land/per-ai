import os
import logging
import httpx
import json
import uuid
from typing import AsyncGenerator, Dict, Optional
from app.service_client.models import (
    AgentQueryRequestContract,
    AgentQueryResponseContract,
    ChatCompletionRequestContract,
)

logger = logging.getLogger(__name__)

class AgentsServiceAsyncClient:
    """
    Asynchronous client for Agents Service.
    Uses httpx.AsyncClient for non-blocking I/O.
    """
    _instance = None

    """
    Singleton pattern to ensure only one instance exists.
    """
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        self.base_url = os.getenv("AGENTS_BASE_URL", "http://localhost:8001")
        self.api_version = os.getenv("INTERNAL_API_VERSION", "v1")
        self.service_token = os.getenv("SERVICE_JWT_TOKEN", "change-me")
        self.api_key = os.getenv("AGENT_API_KEY", "default-insecure-key")
        self.timeout = float(os.getenv("AGENTS_CLIENT_TIMEOUT_SECONDS", "300"))

        # Shared limits
        self.limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self.timeout_config = httpx.Timeout(self.timeout, connect=5.0)

        # Async Client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_config,
            limits=self.limits
        )

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.service_token}",
            "X-API-Key": self.api_key,
            "X-API-Version": self.api_version,
            "X-Request-Id": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }
        return headers

    async def chat_completion_stream(self, payload: ChatCompletionRequestContract) -> AsyncGenerator[str, None]:
        """
        Stream chat completion results from agents service asynchronously.
        """
        # Force stream=True in payload
        payload.stream = True

        headers = self._build_headers()
        url = "/api/v1/chat/completions" # Matches sync client path

        try:
            async with self.client.stream("POST", url, json=payload.model_dump(mode="json"), headers=headers) as response:
                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        await response.aread() # Read content
                        error_data = response.json()
                        error_msg = error_data.get("detail", {}).get("message", response.text)
                    except:
                        pass
                    yield f"Error: {response.status_code} {error_msg}"
                    return

                async for line in response.aiter_lines():
                    if line:
                        yield line
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling agents service: {e}")
            yield f"Error: HTTP {e.response.status_code}"
        except Exception as e:
            logger.error(f"Error calling agents service: {e}")
            yield f"Error: {str(e)}"

    async def query(self, payload: AgentQueryRequestContract) -> AgentQueryResponseContract:
        headers = self._build_headers()
        response = await self.client.post(
            "/api/v1/agents/query",
            json=payload.model_dump(mode="json"),
            headers=headers,
        )
        response.raise_for_status()
        return AgentQueryResponseContract.model_validate(response.json())

    async def query_stream(self, payload: AgentQueryRequestContract) -> AsyncGenerator[Dict, None]:
        """
        Stream a query to the agents service.
        Yields parsed NDJSON event dicts: {"event": "...", "data": {...}}
        """
        headers = self._build_headers()
        try:
            async with self.client.stream(
                "POST",
                "/api/v1/agents/query/stream",
                json=payload.model_dump(mode="json"),
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    await response.aread()
                    yield {"event": "error", "data": {"message": f"HTTP {response.status_code}"}}
                    return
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON in agent stream: %s", line)
        except httpx.HTTPStatusError as e:
            yield {"event": "error", "data": {"message": f"HTTP {e.response.status_code}"}}
        except Exception as e:
            logger.error("Error streaming from agents service: %s", e)
            yield {"event": "error", "data": {"message": str(e)}}

    async def close(self):
        await self.client.aclose()
