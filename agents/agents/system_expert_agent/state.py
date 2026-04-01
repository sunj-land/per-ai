import operator
from typing import Any, Annotated, Dict, List, Optional, TypedDict
from langchain_core.messages import BaseMessage

class SystemExpertState(TypedDict):
    """
    智能对话 Agent 状态结构
    
    Attributes:
        messages: 多轮对话的上下文消息列表
        task: 原始任务或最新请求描述
        intent: 识别出的用户意图
        entities: 提取的实体
        confidence: 意图置信度
        clarification_needed: 是否需要澄清
        knowledge_results: 检索到的知识库结果
        result: 最终生成的回复或状态结果
        error: 错误信息
    """
    messages: Annotated[List[BaseMessage], operator.add]
    task: Dict[str, Any]
    intent: Optional[str]
    entities: Dict[str, Any]
    confidence: float
    clarification_needed: bool
    knowledge_results: List[Dict[str, Any]]
    result: Dict[str, Any]
    error: Optional[str]
