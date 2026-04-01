"""
本文件定义 agents HTTP 服务入口与路由装配逻辑 维护者 SunJie 创建于 2026-03-15 最近修改于 2026-03-15
"""

import logging
import os
from typing import Any, Dict, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from starlette.status import HTTP_403_FORBIDDEN

from api.endpoints import router as master_agent_router
from api.interrupt_endpoints import router as interrupt_router
from api.service import router as unified_llm_router
from core.collaboration import CollaborationManager
from core.manager import AgentManager

# ========== Agent API 工作流 ==========
# +---------+      +-------------------------+      +--------------------------+
# | Client  | ---> | /api/v1/agents/query    | ---> | MasterGraph / Sub-graphs |
# +---------+      +-------------------------+      +--------------------------+
#       \                    |                                 |
#        \-----> /workflow --+-----> CollaborationGraph -------+

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentAPI")

API_KEY = os.getenv("AGENT_API_KEY", "default-insecure-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    校验调用方 API Key

    Args:
        api_key_header: 请求头透传的密钥

    Returns:
        校验通过的密钥文本

    Raises:
        HTTPException: 校验失败抛出 403
    """

    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )


app = FastAPI(title="Intelligent Agent System API", version="1.0.0")
manager = AgentManager()
collaboration_manager = CollaborationManager()


class TaskRequest(BaseModel):
    """
    描述按智能体执行任务的请求体
    """

    task: Dict[str, Any]


class WorkflowRequest(BaseModel):
    """
    描述协作工作流执行请求体
    """

    task: str


class TaskResponse(BaseModel):
    """
    描述通用任务执行响应体
    """

    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


@app.get("/")
async def root():
    """
    返回服务欢迎信息
    """

    return {"message": "Welcome to Intelligent Agent System API"}


@app.post("/workflow", dependencies=[Depends(get_api_key)])
async def execute_workflow(request: WorkflowRequest):
    """
    执行多智能体协作工作流
    """

    try:
        result = await collaboration_manager.run(request.task)
        return {"status": "completed", "result": result}
    except Exception as exc:
        logger.error("Workflow execution failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/agents", response_model=Dict[str, Any], dependencies=[Depends(get_api_key)])
async def list_agents():
    """
    列举全部已注册智能体状态
    """

    return {"agents": manager.list_agents()}


@app.get("/agents/{agent_name}", dependencies=[Depends(get_api_key)])
async def get_agent_status(agent_name: str):
    """
    查询指定智能体状态
    """

    agent = manager.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.get_status()


@app.post("/agents/{agent_name}/task", dependencies=[Depends(get_api_key)])
async def execute_task(agent_name: str, request: TaskRequest):
    """
    调用单个智能体执行任务
    """

    agent = manager.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        result = await agent.execute(request.task)
        return {"status": "completed", "result": result}
    except Exception as exc:
        logger.error("Task execution failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health_check():
    """
    服务健康检查
    """

    return {"status": "ok"}


app.include_router(master_agent_router, prefix="/api/v1/agents", tags=["AgentsV1"])
app.include_router(unified_llm_router, prefix="/api/v1", tags=["LLM"])
app.include_router(interrupt_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("AGENT_HOST", "0.0.0.0"),
        port=int(os.getenv("AGENT_PORT", "8001")),
        reload=os.getenv("AGENT_RELOAD", "false").lower() == "true",
    )
