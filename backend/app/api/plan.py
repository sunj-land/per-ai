from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.core.auth import get_current_active_user, User
from app.models.plan import (
    PlanHeader, PlanHeaderRead, PlanCreateFull,
    PlanMilestone, PlanTask, PlanStatus
)
from app.services.agent_client import agent_client
import logging

logger = logging.getLogger(__name__)

# 创建学习计划相关的 API 路由
router = APIRouter()

@router.post("/generate", response_model=PlanCreateFull, summary="根据目标生成学习计划")
async def generate_plan(
    goal_text: str,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    调用学习规划 Agent (Learning Planning Agent) 根据用户输入的目标文本生成详细的学习计划。
    该接口返回计划结构的预览（PlanCreateFull），此时计划尚未持久化到数据库。

    Args:
        goal_text (str): 用户的学习目标文本。
        current_user (User): 当前认证的用户（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果调用 Agent 或解析结果失败，抛出 500 内部服务器错误。

    Returns:
        dict: 包含计划预览结构的字典，符合 PlanCreateFull 模型格式。
    """
    # 构造传递给 Agent 的任务数据
    task = {"type": "create_plan", "goal_text": goal_text}

    try:
        # 调用 Agent 执行生成任务
        result = await agent_client.execute_task("learning_planner", task)

        # 解析 Agent 返回的目标分析和计划数据
        goal_info = result.get("goal_analysis", {})
        plan_data = result.get("generated_plan", {})

        # 将 Agent 的输出结构转换为与数据库模型匹配的数据列表
        milestones_list = []
        for m in plan_data.get("milestones", []):
            tasks_list = []
            for t in m.get("tasks", []):
                # 构建里程碑下的具体任务
                tasks_list.append({
                    "title": t.get("title"),
                    "type": t.get("type", "other"),
                    "estimated_min": t.get("estimated_min", 30),
                    "description": t.get("description"),
                    "status": "pending"
                })

            # 构建里程碑对象
            milestones_list.append({
                "title": m.get("title"),
                "deadline": m.get("deadline"), # 假设为 ISO 格式的日期字符串
                "tasks": tasks_list,
                "status": "pending"
            })

        # 返回格式化后的计划数据（草稿状态）
        return {
            "user_id": current_user.id,
            "goal": goal_text,
            "deadline": goal_info.get("deadline_date"),
            "estimated_hours": plan_data.get("estimated_total_hours"),
            "difficulty_coef": plan_data.get("difficulty_coef", 1.0),
            "milestones": milestones_list,
            "status": "draft"
        }

    except TimeoutError as e:
        logger.warning(f"Plan generation timeout: {str(e)}")
        raise HTTPException(status_code=504, detail="大模型调用超时")
    except Exception as e:
        # 捕获异常并抛出 HTTP 错误
        logger.error(f"Plan generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")

@router.post("", response_model=PlanHeaderRead, summary="保存生成的学习计划")
async def create_plan(
    plan_data: PlanCreateFull,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    将用户确认的完整学习计划（包括表头、里程碑和任务）保存到数据库中。

    Args:
        plan_data (PlanCreateFull): 包含计划全量数据的对象。
        current_user (User): 当前认证的用户（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        PlanHeaderRead: 保存成功的计划表头信息。
    """
    # 1. 创建计划表头并保存
    plan_header = PlanHeader.from_orm(plan_data)
    plan_header.user_id = current_user.id # 确保计划归属于当前用户
    session.add(plan_header)
    session.commit()
    session.refresh(plan_header) # 刷新获取自动生成的 plan_id

    # 2. 遍历并创建里程碑及其关联任务
    for ms_data in plan_data.milestones:
        # 创建里程碑
        milestone = PlanMilestone.from_orm(ms_data)
        milestone.plan_id = plan_header.plan_id
        session.add(milestone)
        session.commit()
        session.refresh(milestone) # 刷新获取自动生成的 milestone_id

        # 创建该里程碑下的所有任务
        for task_data in ms_data.tasks:
            task = PlanTask.from_orm(task_data)
            task.milestone_id = milestone.milestone_id
            session.add(task)

    # 统一提交所有任务
    session.commit()
    return plan_header

@router.get("", response_model=List[PlanHeaderRead], summary="获取当前用户的所有计划")
async def list_plans(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    获取当前用户所有的学习计划列表。

    Args:
        current_user (User): 当前认证的用户（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[PlanHeaderRead]: 用户的计划表头列表。
    """
    # 查询归属于当前用户的计划
    statement = select(PlanHeader).where(PlanHeader.user_id == current_user.id)
    plans = session.exec(statement).all()
    return plans

@router.get("/{plan_id}", response_model=PlanCreateFull, summary="获取指定计划的详细信息")
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    根据计划 ID 获取单个计划的详细信息，包括里程碑和任务。

    Args:
        plan_id (int): 目标计划的 ID。
        current_user (User): 当前认证的用户（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果找不到计划或计划不属于当前用户，抛出 404 错误。

    Returns:
        PlanCreateFull: 包含里程碑和任务的完整计划信息。
    """
    # 从数据库获取计划
    plan = session.get(PlanHeader, plan_id)

    # 权限及存在性检查
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Plan not found")

    # 注意：这里依赖 SQLModel 的 relationship 正确配置，
    # 使得获取 PlanHeader 时能自动加载相关的 milestones，进而加载 tasks。
    # 从而能够适配 PlanCreateFull 模型的嵌套结构。
    return plan
