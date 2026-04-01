import operator
from typing import Annotated, Sequence, TypedDict, Any, Dict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class DemoAgentState(TypedDict):
    """
    Agent 状态定义，支持短期记忆（对话历史）和额外上下文（长期记忆/变量）。
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # 长期记忆检索结果
    long_term_memory: Dict[str, Any]
    
    # 当前工具执行结果
    tool_results: Dict[str, Any]
    
    # 是否请求中断
    requires_user_input: bool
    
    # 错误状态记录
    error: str | None
