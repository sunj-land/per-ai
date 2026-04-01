from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
import json
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.dependencies import get_schedule_service
from app.services.protocols import ScheduleServiceProtocol
from app.models.schedule import Schedule, ScheduleCreate, ScheduleUpdate, ScheduleReminder

router = APIRouter()


@router.get("/backup", response_model=Dict[str, List[Dict]], summary="备份日程数据")
async def backup_schedules(svc: ScheduleServiceProtocol = Depends(get_schedule_service)):
    return svc.backup_data()


@router.post("/restore", summary="恢复日程数据")
async def restore_schedules(
    file: UploadFile = File(...),
    clear_existing: bool = False,
    svc: ScheduleServiceProtocol = Depends(get_schedule_service),
):
    try:
        content = await file.read()
        data = json.loads(content)
        svc.restore_data(data, clear_existing)
        return {"message": "Data restored successfully", "count": len(data.get("schedules", []))}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Restore failed: {str(e)}")


@router.post("", response_model=Schedule, summary="创建日程")
async def create_schedule(
    schedule_in: ScheduleCreate,
    svc: ScheduleServiceProtocol = Depends(get_schedule_service),
):
    return await svc.create_schedule(schedule_in)


@router.get("", response_model=List[Schedule], summary="获取日程列表")
async def get_schedules(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    svc: ScheduleServiceProtocol = Depends(get_schedule_service),
):
    return await svc.get_schedules(start_time, end_time, limit=limit, offset=offset)


@router.get("/{schedule_id}", response_model=Schedule, summary="获取指定日程")
async def get_schedule(
    schedule_id: UUID,
    svc: ScheduleServiceProtocol = Depends(get_schedule_service),
):
    schedule = await svc.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.put("/{schedule_id}", response_model=Schedule, summary="更新日程")
async def update_schedule(
    schedule_id: UUID,
    schedule_in: ScheduleUpdate,
    svc: ScheduleServiceProtocol = Depends(get_schedule_service),
):
    schedule = await svc.update_schedule(schedule_id, schedule_in)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.delete("/{schedule_id}", summary="删除日程")
async def delete_schedule(
    schedule_id: UUID,
    svc: ScheduleServiceProtocol = Depends(get_schedule_service),
):
    success = await svc.delete_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "success"}


@router.get("/{schedule_id}/reminders", response_model=List[ScheduleReminder], summary="获取日程提醒")
async def get_schedule_reminders(
    schedule_id: UUID,
    session: Session = Depends(get_session),
):
    reminders = session.exec(
        select(ScheduleReminder).where(ScheduleReminder.schedule_id == schedule_id)
    ).all()
    return reminders
