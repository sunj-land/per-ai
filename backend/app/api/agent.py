"""
Agent (智能体) API 路由模块
负责处理智能体相关的所有接口请求，包括同步本地智能体、列表查询以及获取图谱结构等。
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_agent_center_catalog_service, get_agent_service
from app.models.agent_store import AgentModel
from app.services.agent_center_catalog_service import (
    DataPathNotFoundError,
    DuplicateIdConflictError,
    FileParseError,
)

router = APIRouter()


def ok(data: Any = None, msg: str = "success") -> Dict[str, Any]:
    return {"code": 0, "msg": msg, "data": data}


def fail(msg: str, code: int = 1, data: Any = None) -> Dict[str, Any]:
    return {"code": code, "msg": msg, "data": data}


def error_response(status_code: int, msg: str, data: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "msg": msg, "data": data},
    )


@router.post("/sync")
async def sync_agents(
    session: Session = Depends(get_session),
    catalog=Depends(get_agent_center_catalog_service),
):
    try:
        catalog.refresh("agents")
        result = catalog.get_items("agents")
        return ok(result)
    except DuplicateIdConflictError as exc:
        return error_response(400, "duplicate agent id conflict", {"conflicts": exc.conflicts})
    except FileParseError as exc:
        return error_response(422, "agent data parse failed", {"errors": exc.errors})
    except DataPathNotFoundError as exc:
        return error_response(422, "agent data path not found", {"path": exc.path, "type": exc.data_type})
    except Exception as exc:
        catalog.log_internal_error("sync agents failed", exc)
        return error_response(500, "internal server error")


@router.get("")
async def list_agents(
    page: Optional[int] = Query(default=None, ge=1),
    size: Optional[int] = Query(default=None, ge=1, le=200),
    session: Session = Depends(get_session),
    catalog=Depends(get_agent_center_catalog_service),
):
    try:
        _ = session
        agents = catalog.get_items("agents", page=page, size=size)
        return ok(agents)
    except DuplicateIdConflictError as exc:
        return error_response(400, "duplicate agent id conflict", {"conflicts": exc.conflicts})
    except FileParseError as exc:
        return error_response(422, "agent data parse failed", {"errors": exc.errors})
    except DataPathNotFoundError as exc:
        return error_response(422, "agent data path not found", {"path": exc.path, "type": exc.data_type})
    except Exception as exc:
        catalog.log_internal_error("list agents failed", exc)
        return error_response(500, "internal server error")


@router.get("/{agent_id}/graph")
async def get_agent_graph(
    agent_id: uuid.UUID,
    session: Session = Depends(get_session),
    svc=Depends(get_agent_service),
):
    try:
        agent = session.get(AgentModel, agent_id)
        if not agent:
            return fail("Agent not found", code=404)
        mermaid = await svc.get_graph_mermaid(agent.name)
        return ok({"mermaid": mermaid})
    except Exception as e:
        return fail(str(e), code=500)
