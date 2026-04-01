import os
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
import httpx
from app.core.auth import get_current_active_user, User

logger = logging.getLogger(__name__)
router = APIRouter()

AGENTS_BASE_URL = os.getenv("AGENTS_BASE_URL", "http://localhost:8001")
SERVICE_JWT_TOKEN = os.getenv("SERVICE_JWT_TOKEN", "change-me")
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "default-insecure-key")

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_agents_requests(request: Request, path: str, current_user: User = Depends(get_current_active_user)):
    """
    通用代理转发，将所有 /api/v1/agents/* 请求转发到专门的 agents 服务集群。
    实现请求/响应数据的格式转换和协议适配，支持流式传输。
    """
    target_url = f"{AGENTS_BASE_URL}/api/v1/agents/{path}"

    # 转发请求头，剔除 host 等容易引起冲突的头部
    headers = dict(request.headers)
    headers.pop("host", None)
    
    # 替换认证信息为 agents 内部服务 token，跳过 agents 的权限校验
    headers["Authorization"] = f"Bearer {SERVICE_JWT_TOKEN}"
    headers["X-API-Key"] = AGENT_API_KEY

    try:
        body = await request.body()
    except Exception as e:
        logger.error(f"Error reading request body: {e}")
        body = b""

    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    # 构建请求
    req = client.build_request(
        method=request.method,
        url=target_url,
        headers=headers,
        content=body,
        params=request.query_params
    )

    import time
    start_time = time.time()

    try:
        # 使用 stream 发送请求并流式响应
        response = await client.send(req, stream=True)

        # 准备返回的 header
        response_headers = dict(response.headers)
        response_headers.pop("content-encoding", None)
        response_headers.pop("content-length", None)

        async def stream_generator():
            try:
                async for chunk in response.aiter_raw():
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()
                elapsed = time.time() - start_time
                logger.info(f"Proxy request {request.method} {target_url} completed with status {response.status_code} in {elapsed:.3f}s")

        return StreamingResponse(
            stream_generator(),
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get("content-type")
        )
    except httpx.RequestError as e:
        elapsed = time.time() - start_time
        logger.error(f"Proxy request error to {target_url} after {elapsed:.3f}s: {e}")
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Bad Gateway: Error communicating with agents service. {str(e)}")
