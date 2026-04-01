from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_rss_quality_service
from app.models.rss_quality import (
    RSSQualityBatchScoreRequest,
    RSSQualityResultQuery,
    RSSQualityRuleUpdate,
)

router = APIRouter()


def ok(data: Any = None, msg: str = "success") -> Dict[str, Any]:
    return {"code": 0, "msg": msg, "data": data}


def error_response(status_code: int, msg: str, data: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "msg": msg, "data": data},
    )


@router.get("/config")
def get_rss_quality_config(
    session: Session = Depends(get_session),
    svc=Depends(get_rss_quality_service),
):
    try:
        rule = svc.get_active_rule(session)
        return ok(svc.serialize_rule(rule))
    except Exception as exc:
        return error_response(500, "failed to load rss quality config", {"error": str(exc)})


@router.get("/config/default")
def get_default_rss_quality_config(svc=Depends(get_rss_quality_service)):
    return ok(svc.get_default_config())


@router.put("/config")
def update_rss_quality_config(
    payload: RSSQualityRuleUpdate,
    session: Session = Depends(get_session),
    svc=Depends(get_rss_quality_service),
):
    try:
        rule = svc.update_rule(session, payload)
        return ok(svc.serialize_rule(rule))
    except Exception as exc:
        return error_response(500, "failed to update rss quality config", {"error": str(exc)})


@router.post("/score")
async def batch_score_rss_articles(
    payload: RSSQualityBatchScoreRequest,
    svc=Depends(get_rss_quality_service),
):
    try:
        result = await svc.score_articles(payload)
        return ok(result)
    except Exception as exc:
        return error_response(500, "failed to score rss articles", {"error": str(exc)})


@router.get("/results")
def list_rss_quality_results(
    min_score: Optional[float] = Query(default=None, ge=0, le=100),
    max_score: Optional[float] = Query(default=None, ge=0, le=100),
    feed_id: Optional[int] = Query(default=None),
    batch_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    svc=Depends(get_rss_quality_service),
):
    try:
        query = RSSQualityResultQuery(
            min_score=min_score, max_score=max_score, feed_id=feed_id,
            batch_id=batch_id, status=status, limit=limit,
        )
        return ok(svc.list_results(session, query))
    except Exception as exc:
        return error_response(500, "failed to load rss quality results", {"error": str(exc)})


@router.get("/logs")
def list_rss_quality_logs(
    batch_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
    svc=Depends(get_rss_quality_service),
):
    try:
        return ok(svc.list_logs(session, batch_id=batch_id, limit=limit))
    except Exception as exc:
        return error_response(500, "failed to load rss quality logs", {"error": str(exc)})
