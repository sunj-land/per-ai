"""
Skill (技能) API 路由模块
负责处理技能相关的所有接口请求，包括技能的同步、创建、安装、更新、卸载及流式状态查询等。
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import (
    get_agent_center_catalog_service,
    get_skill_install_progress_service,
    get_skill_service,
)
from app.models.agent_store import SkillModel
from app.services.agent_center_catalog_service import (
    DataPathNotFoundError,
    DuplicateIdConflictError,
    FileParseError,
)

router = APIRouter()


class SkillInstallRequest(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    url: Optional[str] = None
    operation: str = "install"


class SkillCreateRequest(BaseModel):
    name: str
    description: str


class SkillUpdateRequest(BaseModel):
    markdown: str


class SkillUpgradeRequest(BaseModel):
    version: Optional[str] = None


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
async def sync_skills(
    session: Session = Depends(get_session),
    catalog=Depends(get_agent_center_catalog_service),
):
    try:
        _ = session
        catalog.refresh("skills")
        result = catalog.get_items("skills")
        return ok(result)
    except DuplicateIdConflictError as exc:
        return error_response(400, "duplicate skill id conflict", {"conflicts": exc.conflicts})
    except FileParseError as exc:
        return error_response(422, "skill data parse failed", {"errors": exc.errors})
    except DataPathNotFoundError as exc:
        return error_response(422, "skill data path not found", {"path": exc.path, "type": exc.data_type})
    except Exception as exc:
        catalog.log_internal_error("sync skills failed", exc)
        return error_response(500, "internal server error")


@router.get("")
async def list_skills(
    page: Optional[int] = Query(default=None, ge=1),
    size: Optional[int] = Query(default=None, ge=1, le=200),
    session: Session = Depends(get_session),
    catalog=Depends(get_agent_center_catalog_service),
):
    try:
        _ = session
        skills = catalog.get_items("skills", page=page, size=size)
        return ok(skills)
    except DuplicateIdConflictError as exc:
        return error_response(400, "duplicate skill id conflict", {"conflicts": exc.conflicts})
    except FileParseError as exc:
        return error_response(422, "skill data parse failed", {"errors": exc.errors})
    except DataPathNotFoundError as exc:
        return error_response(422, "skill data path not found", {"path": exc.path, "type": exc.data_type})
    except Exception as exc:
        catalog.log_internal_error("list skills failed", exc)
        return error_response(500, "internal server error")


@router.post("/create")
def create_skill(
    req: SkillCreateRequest,
    session: Session = Depends(get_session),
    svc=Depends(get_skill_service),
):
    try:
        skill = svc.create_skill(session, req.name, req.description)
        return ok(skill, msg="created")
    except ValueError as e:
        return fail(str(e), code=400)
    except Exception as e:
        return fail(str(e), code=500)


@router.post("/install")
async def install_skill(
    req: SkillInstallRequest,
    session: Session = Depends(get_session),
    x_user_id: Optional[str] = Header(default="anonymous"),
    x_idempotency_key: Optional[str] = Header(default=None),
    svc=Depends(get_skill_service),
):
    try:
        if req.url and not req.name:
            result = await svc.install_from_url(session, req.url)
            return ok(result, msg="install started")
        if not req.name:
            return fail("name is required for hub install", code=400)
        result = await svc.install_from_hub(
            session=session,
            skill_name=req.name,
            version=req.version,
            operator=x_user_id or "anonymous",
            source_url=req.url,
            operation=req.operation,
            idempotency_key=x_idempotency_key,
        )
        return ok(result, msg="install started")
    except ValueError as e:
        return fail(str(e), code=400)
    except Exception as e:
        return fail(str(e), code=500)


@router.get("/hub/search")
async def search_skillhub(
    name: Optional[str] = Query(default=None),
    tags: Optional[str] = Query(default=None),
    version: Optional[str] = Query(default=None),
    svc=Depends(get_skill_service),
):
    try:
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        result = await svc.search_skillhub(name=name, tags=tag_list, version=version)
        return ok(result)
    except Exception as e:
        return fail(str(e), code=500)


@router.get("/install-records")
def get_install_records(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    session: Session = Depends(get_session),
    svc=Depends(get_skill_service),
):
    try:
        records = svc.list_install_records(session=session, offset=offset, limit=limit)
        return ok(records)
    except Exception as e:
        return fail(str(e), code=500)


@router.get("/install/{task_id}/status")
def get_install_status(
    task_id: str,
    progress_svc=Depends(get_skill_install_progress_service),
):
    return ok(progress_svc.snapshot(task_id))


@router.get("/install/{task_id}/stream")
async def stream_install(
    task_id: str,
    progress_svc=Depends(get_skill_install_progress_service),
):
    async def event_generator():
        async for event in progress_svc.stream(task_id):
            payload = ok(event)
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{skill_id}")
def get_skill(
    skill_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    try:
        skill = session.get(SkillModel, skill_id)
        if not skill:
            return fail("Skill not found", code=404)
        return ok(skill)
    except Exception as e:
        return fail(str(e), code=500)


@router.get("/{skill_id}/markdown")
def get_skill_markdown(
    skill_id: uuid.UUID,
    session: Session = Depends(get_session),
    svc=Depends(get_skill_service),
):
    try:
        skill = session.get(SkillModel, skill_id)
        if not skill:
            return fail("Skill not found", code=404)
        markdown = svc.get_skill_markdown(skill.name)
        return ok({"markdown": markdown})
    except Exception as e:
        return fail(str(e), code=500)


@router.put("/{skill_id}/markdown")
def update_skill_markdown(
    skill_id: uuid.UUID,
    req: SkillUpdateRequest,
    session: Session = Depends(get_session),
    svc=Depends(get_skill_service),
):
    try:
        skill = session.get(SkillModel, skill_id)
        if not skill:
            return fail("Skill not found", code=404)
        svc.update_skill_markdown(skill.name, req.markdown)
        if len(req.markdown) > 0:
            skill.description = req.markdown[:200] + "..." if len(req.markdown) > 200 else req.markdown
            skill.updated_at = datetime.utcnow()
            session.add(skill)
            session.commit()
        return ok({"status": "success"})
    except Exception as e:
        return fail(str(e), code=500)


@router.post("/{skill_id}/uninstall")
async def uninstall_skill(
    skill_id: uuid.UUID,
    session: Session = Depends(get_session),
    x_user_id: Optional[str] = Header(default="anonymous"),
    svc=Depends(get_skill_service),
):
    try:
        result = await svc.uninstall_skill(
            session=session, skill_id=skill_id, operator=x_user_id or "anonymous"
        )
        return ok(result, msg="uninstalled")
    except ValueError as e:
        return fail(str(e), code=400)
    except Exception as e:
        return fail(str(e), code=500)


@router.post("/{skill_id}/upgrade")
async def upgrade_skill(
    skill_id: uuid.UUID,
    req: SkillUpgradeRequest,
    session: Session = Depends(get_session),
    x_user_id: Optional[str] = Header(default="anonymous"),
    x_idempotency_key: Optional[str] = Header(default=None),
    svc=Depends(get_skill_service),
):
    try:
        result = await svc.upgrade_skill(
            session=session,
            skill_id=skill_id,
            version=req.version,
            operator=x_user_id or "anonymous",
            idempotency_key=x_idempotency_key,
        )
        return ok(result, msg="upgrade started")
    except ValueError as e:
        return fail(str(e), code=400)
    except Exception as e:
        return fail(str(e), code=500)


@router.get("/{skill_id}/versions")
async def get_skill_versions(
    skill_id: uuid.UUID,
    session: Session = Depends(get_session),
    svc=Depends(get_skill_service),
):
    try:
        skill = session.get(SkillModel, skill_id)
        if not skill:
            return fail("Skill not found", code=404)
        versions = await svc.list_versions(skill.name)
        return ok(versions)
    except Exception as e:
        return fail(str(e), code=500)
