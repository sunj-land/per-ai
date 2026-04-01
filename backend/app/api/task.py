from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select
from app.core.database import get_session
from app.core.dependencies import get_task_service
from app.services.protocols import TaskServiceProtocol
from app.models.task import Task, TaskCreate, TaskUpdate, TaskLog

router = APIRouter()


@router.get("", response_model=List[Task])
async def get_tasks(session: Session = Depends(get_session)):
    tasks = session.exec(select(Task)).all()
    return tasks


@router.post("", response_model=Task)
async def create_task(
    task_in: TaskCreate,
    svc: TaskServiceProtocol = Depends(get_task_service),
):
    task = Task.from_orm(task_in)
    return await svc.create_task(task)


@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: UUID,
    task_in: TaskUpdate,
    svc: TaskServiceProtocol = Depends(get_task_service),
):
    update_data = task_in.dict(exclude_unset=True)
    task = await svc.update_task(task_id, update_data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    svc: TaskServiceProtocol = Depends(get_task_service),
):
    success = await svc.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success"}


@router.post("/{task_id}/run")
async def run_task(
    task_id: UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    svc: TaskServiceProtocol = Depends(get_task_service),
):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    background_tasks.add_task(svc.execute_task, task_id)
    return {"status": "triggered"}


@router.post("/{task_id}/pause")
async def pause_task(
    task_id: UUID,
    svc: TaskServiceProtocol = Depends(get_task_service),
):
    task = await svc.pause_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/resume")
async def resume_task(
    task_id: UUID,
    svc: TaskServiceProtocol = Depends(get_task_service),
):
    task = await svc.resume_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/logs", response_model=List[TaskLog])
async def get_task_logs(
    task_id: UUID,
    limit: int = Query(20, le=100),
    session: Session = Depends(get_session),
):
    logs = session.exec(
        select(TaskLog)
        .where(TaskLog.task_id == task_id)
        .order_by(TaskLog.created_at.desc())
        .limit(limit)
    ).all()
    return logs
