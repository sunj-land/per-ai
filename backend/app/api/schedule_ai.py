from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
from app.core.dependencies import get_schedule_service
from app.services.protocols import ScheduleServiceProtocol

# Placeholder for ScheduleAgent to avoid breaking the backend since agents are decoupled
class MockScheduleAgent:
    def __init__(self):
        self.skills = {}

router = APIRouter(tags=["Schedule AI"])
agent = MockScheduleAgent()

# --- AI Integration ---

class AISearchRequest(BaseModel):
    """
    AI 搜索请求模型，包含自然语言查询字符串及返回条数限制。
    """
    query: str
    limit: int = 10

class AISearchResponse(BaseModel):
    """
    AI 搜索响应模型，包含解析后的时间范围及搜索结果。
    """
    query: str
    parsed_time_range: Optional[Dict[str, Optional[datetime]]]
    results: List[Dict[str, Any]]

def parse_natural_language_time(query: str) -> Dict[str, Optional[datetime]]:
    """
    基于简单规则的自然语言时间解析器（演示用途）。
    从查询字符串中提取出“今天”、“明天”、“下周”等时间意图，并转换为 datetime 范围。

    Args:
        query (str): 自然语言查询字符串。

    Returns:
        Dict[str, Optional[datetime]]: 包含 start_time 和 end_time 的字典。
    """
    now = datetime.now()
    query = query.lower()

    start_time = None
    end_time = None

    if "today" in query or "今天" in query:
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
    elif "tomorrow" in query or "明天" in query:
        start_time = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
    elif "next week" in query or "下周" in query:
        # Start of next week (assuming Monday) / 下周开始（假设为周一）
        days_ahead = 7 - now.weekday()
        start_time = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=7)

    return {"start_time": start_time, "end_time": end_time}

@router.post("/search", response_model=AISearchResponse, summary="AI 智能搜索日程")
async def search_schedules_ai(
    request: AISearchRequest,
    svc: ScheduleServiceProtocol = Depends(get_schedule_service),
):
    """
    使用 AI 解析自然语言搜索日程记录。
    业务逻辑：
    1. 使用规则或 AI 模型解析自然语言中的时间范围。
    2. 提取剩余的关键字。
    3. 调用 schedule_service 获取匹配的日程。
    4. 将日程格式化为紧凑的数据结构返回。

    Args:
        request (AISearchRequest): 搜索请求数据。

    Returns:
        AISearchResponse: 解析结果和匹配的日程列表。
    """
    time_range = parse_natural_language_time(request.query)

    # Extract keyword if not time related (naive implementation)
    # In a real scenario, we would remove the time-related words from the query
    # 提取查询关键字（简单实现：移除时间相关的词汇）
    keyword = request.query
    for time_word in ["today", "tomorrow", "next week", "今天", "明天", "下周"]:
        keyword = keyword.replace(time_word, "").strip()

    if not keyword:
        keyword = None

    schedules = await svc.get_schedules(
        start_time=time_range["start_time"],
        end_time=time_range["end_time"],
        keyword=keyword,
        limit=request.limit
    )

    # Format for AI: compact representation
    # 为 AI 格式化结果，提供紧凑表示
    formatted_results = []
    for s in schedules:
        formatted_results.append({
            "id": str(s.id),
            "title": s.title,
            "start": s.start_time.isoformat(),
            "end": s.end_time.isoformat() if s.end_time else None,
            "priority": s.priority,
            "status": "active" # Assuming active, as status field might not exist on Schedule model or logic differs / 假设为 active，因为 Schedule 模型上可能没有状态字段
        })

    return {
        "query": request.query,
        "parsed_time_range": time_range,
        "results": formatted_results
    }

# --- MCP Integration ---

@router.get("/mcp/tools", summary="获取 MCP 工具列表")
async def get_mcp_tools():
    """
    以 MCP (Model Context Protocol) 格式（JSON Schema）返回当前可用的 AI 技能工具。

    Returns:
        dict: 包含可用工具列表的字典。
    """
    tools = []
    for name, skill in agent.skills.items():
        tools.append({
            "name": name,
            "description": skill.description,
            "inputSchema": {
                "type": "object",
                "properties": skill.input_schema
            }
        })
    return {"tools": tools}

class MCPCallRequest(BaseModel):
    """
    MCP 工具调用请求模型。
    """
    tool_name: str
    arguments: Dict[str, Any]

@router.post("/mcp/call", summary="调用 MCP 工具")
async def call_mcp_tool(request: MCPCallRequest):
    """
    执行指定的 MCP 工具（技能）。

    业务逻辑：
    1. 验证请求的工具是否存在。
    2. 调用 agent.skills 中的目标工具的 execute 方法。
    3. 捕获并返回执行结果或错误信息。

    Args:
        request (MCPCallRequest): 工具调用请求数据。

    Returns:
        dict: 执行结果（遵循 MCP 协议格式）。

    Raises:
        HTTPException: 如果请求的工具不存在，抛出 404 错误。
    """
    if request.tool_name not in agent.skills:
        raise HTTPException(status_code=404, detail=f"Tool {request.tool_name} not found")

    try:
        result = await agent.skills[request.tool_name].execute(request.arguments)
        # Format as MCP content / 格式化为 MCP 内容
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
