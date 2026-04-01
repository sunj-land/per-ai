import pytest
import asyncio
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agents.comprehensive_demo_agent.graph import ComprehensiveDemoAgent
from agents.comprehensive_demo_agent.tools import calculator, web_search, file_operation
from agents.comprehensive_demo_agent.state import DemoAgentState

@pytest.mark.asyncio
async def test_tools_calculator():
    res = await calculator.ainvoke({"expression": "2 + 3 * 4"})
    assert "14" in res

    # 测试非法字符
    res_err = await calculator.ainvoke({"expression": "import os"})
    assert "错误" in res_err

@pytest.mark.asyncio
async def test_tools_web_search():
    res = await web_search.ainvoke({"query": "deepseek"})
    assert "DeepSeek" in res

@pytest.mark.asyncio
async def test_tools_file_operation():
    # 测试写入
    write_res = await file_operation.ainvoke({"action": "write", "filename": "test.txt", "content": "hello world"})
    assert "成功" in write_res

    # 测试读取
    read_res = await file_operation.ainvoke({"action": "read", "filename": "test.txt"})
    assert "hello world" in read_res

@pytest.mark.asyncio
async def test_agent_process_task():
    agent = ComprehensiveDemoAgent()
    # 模拟简单的查询
    result = await agent.process_task({
        "query": "你好",
        "thread_id": "test_thread_1"
    })
    assert result.get("status") == "success"
    assert isinstance(result.get("answer"), str)

@pytest.mark.asyncio
async def test_agent_interrupt_logic():
    agent = ComprehensiveDemoAgent()

    # 直接测试 route 逻辑
    state: DemoAgentState = {
        "messages": [AIMessage(content="", tool_calls=[{"name": "file_operation", "args": {"action": "write"}, "id": "1"}])],
        "requires_user_input": True,
        "error": None
    }

    next_node = agent._route_agent_output(state)
    assert next_node == "human_review"

@pytest.mark.asyncio
async def test_agent_action_logic():
    agent = ComprehensiveDemoAgent()

    state: DemoAgentState = {
        "messages": [AIMessage(content="", tool_calls=[{"name": "calculator", "args": {"expression": "1+1"}, "id": "1"}])],
        "requires_user_input": False,
        "error": None
    }

    next_node = agent._route_agent_output(state)
    assert next_node == "action"

    # 测试执行 action 节点
    result = await agent._call_tools(state)
    assert "tool_results" in result
    assert "messages" in result
    assert result["tool_results"]["calculator"] == "计算结果: 2"
