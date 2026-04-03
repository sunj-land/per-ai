from datetime import date, datetime, UTC
import json
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from core.master_agent import MasterAgent
from core.protocol import AgentRequest, AgentResponse
from core.conversation_logger import conversation_logger
from pydantic import BaseModel, Field, HttpUrl
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Singleton Master Agent
master_agent = MasterAgent()


class AgentLogUploadRequest(BaseModel):
    start_date: date = Field(description="开始日期，格式 YYYY-MM-DD")
    end_date: date = Field(description="结束日期，格式 YYYY-MM-DD")
    upload_url: HttpUrl = Field(description="分析平台上传地址")
    delete_after_upload: bool = Field(default=False, description="上传成功后是否删除本地日志")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="上传超时秒数")


def _error_payload(
    code: str,
    message: str,
    trace_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "trace_id": trace_id,
            "details": details or {},
        }
    }


async def verify_service_auth(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_version: Optional[str] = Header(default=None),
) -> None:
    required_version = os.getenv("INTERNAL_API_VERSION", "v1")
    if (x_api_version or required_version) != required_version:
        raise HTTPException(
            status_code=400,
            detail=_error_payload(
                code="API_VERSION_MISMATCH",
                message=f"Unsupported API version, expected {required_version}",
                trace_id=request.headers.get("X-Trace-Id"),
            ),
        )

    auth_mode = os.getenv("SERVICE_AUTH_MODE", "jwt").lower()
    if auth_mode == "none":
        return
    if auth_mode == "jwt":
        expected = os.getenv("SERVICE_JWT_TOKEN", "change-me")
        token = (authorization or "").replace("Bearer ", "")
        if token != expected:
            raise HTTPException(
                status_code=401,
                detail=_error_payload(
                    code="UNAUTHORIZED",
                    message="Invalid service token",
                    trace_id=request.headers.get("X-Trace-Id"),
                ),
            )
        return
    if auth_mode == "mtls":
        client_dn = request.headers.get("X-Client-DN")
        if not client_dn:
            raise HTTPException(
                status_code=401,
                detail=_error_payload(
                    code="MTLS_REQUIRED",
                    message="Missing mTLS client identity",
                    trace_id=request.headers.get("X-Trace-Id"),
                ),
            )
        return
    raise HTTPException(
        status_code=500,
        detail=_error_payload(
            code="AUTH_MODE_INVALID",
            message="Unsupported auth mode",
            trace_id=request.headers.get("X-Trace-Id"),
        ),
    )


@router.post("/query", response_model=AgentResponse, summary="Query the Master Agent")
async def query_agent(request: AgentRequest, _: None = Depends(verify_service_auth)):
    """
    Send a query to the Master Agent.
    It will automatically route to Sub-Agents or General Chat.
    """
    try:
        response = await master_agent.process_request(request)
        conversation_logger.log(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "sessionId": request.session_id,
                "userId": request.parameters.get("user_id"),
                "userInput": request.query,
                "history": [message.model_dump(mode="json") for message in request.history],
                "promptTemplate": request.parameters.get("prompt_template"),
                "modelVersion": request.parameters.get("model_version", master_agent.model_name),
                "temperature": request.parameters.get("temperature", 0.7),
                "maxTokens": request.parameters.get("max_tokens"),
                "modelResponse": response.answer,
                "chainOfThought": request.parameters.get("chain_of_thought"),
                "latencyMs": response.latency_ms,
                "tokenUsage": response.metadata.get("token_usage"),
                "metadata": response.metadata,
                "exception": response.error,
            }
        )
        return response
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        raise HTTPException(status_code=500, detail=_error_payload(code="AGENT_QUERY_FAILED", message=str(e)))

@router.post("/query/stream", summary="Stream Query the Master Agent")
async def query_agent_stream(request: AgentRequest, _: None = Depends(verify_service_auth)):
    """
    Stream a query to the Master Agent as NDJSON.
    Each line is a JSON object with {"event": "...", "data": {...}}.
    Events: routing | reasoning | tool_call | done | error
    """
    async def _generate():
        try:
            async for event in master_agent.process_request_stream(request):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as e:
            logger.error("Streaming agent query failed: %s", e)
            yield json.dumps({"event": "error", "data": {"message": str(e)}}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        _generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",   # disable nginx buffering
            "Transfer-Encoding": "chunked",
        },
    )


@router.get("/status", summary="Get Agent System Status")
def get_status(_: None = Depends(verify_service_auth)):
    """
    Get the status of the Agent System.
    """
    return {
        "status": "online",
        "master_agent": "active",
        "sub_agents": ["article_query_agent"],
        "llm_provider": "backend-internal-completion",
    }


@router.get("/health", summary="Get Agent Service Health")
def get_health(_: None = Depends(verify_service_auth)):
    return {"status": "ok"}


@router.post("/logs/upload", summary="Upload agent conversation logs")
def upload_agent_logs(payload: AgentLogUploadRequest, _: None = Depends(verify_service_auth)):
    if payload.start_date > payload.end_date:
        raise HTTPException(
            status_code=400,
            detail=_error_payload(code="INVALID_DATE_RANGE", message="start_date cannot be greater than end_date"),
        )
    try:
        result = conversation_logger.upload_logs(
            start_date=payload.start_date,
            end_date=payload.end_date,
            upload_url=str(payload.upload_url),
            delete_after_upload=payload.delete_after_upload,
            timeout_seconds=payload.timeout_seconds,
        )
        return {
            "uploaded_files": result.uploaded_files,
            "uploaded_bytes": result.uploaded_bytes,
            "deleted_files": result.deleted_files,
            "request_status_code": result.request_status_code,
            "response_body": result.response_body,
        }
    except Exception as exc:
        logger.error("上传对话日志失败: %s", exc)
        raise HTTPException(status_code=500, detail=_error_payload(code="UPLOAD_LOG_FAILED", message=str(exc)))
