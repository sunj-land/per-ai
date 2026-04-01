"""
本文件定义 MasterGraph 与 CollaborationGraph 的共享状态协议 维护者 SunJie 创建于 2026-03-15 最近修改于 2026-03-15
"""

import operator
from typing import Any, Annotated, Dict, List, Optional, TypedDict

from core.protocol import AgentRequest


class MasterAgentState(TypedDict):
    """
    描述主图在节点间传递的状态结构

    Attributes:
        request: 统一请求协议对象
        intent: 意图分类结果
        intent_confidence: 意图分类置信度
        article_results: 检索结果
        final_response: 最终回复文本
        messages: 节点间可追加消息
        error: 异常信息
    """

    request: AgentRequest
    intent: Optional[str]
    intent_confidence: float
    article_results: Optional[Dict[str, Any]]
    final_response: Optional[str]
    messages: Annotated[List[Dict[str, str]], operator.add]
    error: Optional[str]


class CollaborationState(TypedDict):
    """
    描述协作图在多智能体任务流中的状态结构

    Attributes:
        task: 用户任务描述
        plan: 任务拆解步骤列表
        current_step: 当前执行步索引
        results: 聚合执行结果
        final_response: 最终汇总文本
        messages: 节点输出消息
    """

    task: str
    plan: List[str]
    current_step: int
    results: Annotated[Dict[str, Any], operator.ior]
    final_response: str
    messages: Annotated[List[Dict[str, str]], operator.add]


class StandardAgentState(TypedDict):
    """
    标准 Agent 状态结构，用于通用任务处理

    Attributes:
        task: 原始任务参数
        task_type: 任务类型（用于路由）
        result: 执行结果
        error: 错误信息
    """
    task: Dict[str, Any]
    task_type: Optional[str]
    result: Dict[str, Any]
    error: Optional[str]
