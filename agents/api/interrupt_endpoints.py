import logging
import sys
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Lazy load graphs to avoid circular imports and path issues during test discovery
AGENT_GRAPHS = {}

def get_agent_graph(agent_id: str):
    global AGENT_GRAPHS
    if not AGENT_GRAPHS:
        try:
            from agents.entries import (
                image_agent_graph,
                content_generator_agent_graph,
                system_expert_agent_graph,
                workflow_agent_graph,
                data_agent_graph,
                text_agent_graph,
                article_agent_graph,
                learning_planner_agent_graph,
                comprehensive_demo_agent_graph
            )

            AGENT_GRAPHS = {
                "image_agent": image_agent_graph,
                "content_generator_agent": content_generator_agent_graph,
                "system_expert_agent": system_expert_agent_graph,
                "workflow_agent": workflow_agent_graph,
                "data_agent": data_agent_graph,
                "text_agent": text_agent_graph,
                "article_agent": article_agent_graph,
                "learning_planner_agent": learning_planner_agent_graph,
                "comprehensive_demo_agent": comprehensive_demo_agent_graph
            }
        except ImportError as e:
            logger.error(f"Failed to load agent graphs: {e}")

    return AGENT_GRAPHS.get(agent_id)

router = APIRouter(prefix="/v1/agents", tags=["Agent Interrupts"])
logger = logging.getLogger(__name__)

class AgentStartRequest(BaseModel):
    agent_id: str = Field(description="Agent 标识，如 comprehensive_demo_agent")
    thread_id: str = Field(description="会话的唯一标识，用于维护状态")
    input_data: Dict[str, Any] = Field(description="启动 Agent 时的初始输入数据")

class AgentResumeRequest(BaseModel):
    agent_id: str = Field(description="Agent 标识")
    thread_id: str = Field(description="会话的唯一标识")
    user_feedback: Optional[Dict[str, Any]] = Field(default=None, description="用户确认或提供的反馈数据")

@router.post("/start", summary="启动 Agent 任务")
async def start_agent(request: AgentStartRequest):
    graph = get_agent_graph(request.agent_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found")

    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        # 执行图，直到遇到中断或结束
        state = await graph.ainvoke(request.input_data, config=config)

        # 检查是否因为中断而挂起
        current_state = graph.get_state(config)
        if current_state.next:
            return {
                "status": "interrupted",
                "thread_id": request.thread_id,
                "pending_nodes": current_state.next,
                "state": state
            }

        return {
            "status": "completed",
            "thread_id": request.thread_id,
            "state": state
        }
    except Exception as e:
        logger.error(f"Failed to start agent {request.agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/status/{thread_id}", summary="获取 Agent 任务状态")
async def get_agent_status(agent_id: str, thread_id: str):
    graph = get_agent_graph(agent_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    config = {"configurable": {"thread_id": thread_id}}

    try:
        current_state = graph.get_state(config)

        if not current_state or not current_state.values:
            raise HTTPException(status_code=404, detail="State not found for given thread_id")

        return {
            "status": "interrupted" if current_state.next else "completed",
            "thread_id": thread_id,
            "pending_nodes": current_state.next,
            "state": current_state.values
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for {agent_id}/{thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume", summary="恢复被中断的 Agent 任务")
async def resume_agent(request: AgentResumeRequest):
    graph = get_agent_graph(request.agent_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found")

    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        # 验证当前确实处于挂起状态
        current_state = graph.get_state(config)
        if not current_state or not current_state.next:
            raise HTTPException(status_code=400, detail="Agent is not in interrupted state")

        # 如果用户提供了反馈，可以先更新状态。这里使用 ainvoke 直接传入 None 让它继续执行，
        # 如果需要更新特定节点的状态，可以使用 update_state
        # 此处简化为如果有反馈则先合并到当前状态
        if request.user_feedback:
            # 假设反馈是更新当前状态
            graph.update_state(config, request.user_feedback)

        # 恢复执行
        state = await graph.ainvoke(None, config=config)

        # 检查是否再次中断
        new_state = graph.get_state(config)
        if new_state.next:
            return {
                "status": "interrupted",
                "thread_id": request.thread_id,
                "pending_nodes": new_state.next,
                "state": state
            }

        return {
            "status": "completed",
            "thread_id": request.thread_id,
            "state": state
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume agent {request.agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
