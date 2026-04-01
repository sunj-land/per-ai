import pytest
import asyncio
from langchain_core.messages import HumanMessage
from agents.system_expert_agent.graph import SystemExpertAgent

@pytest.mark.asyncio
async def test_system_expert_agent_process_task():
    agent = SystemExpertAgent()
    task = {"query": "如何重置系统密码"}
    result = await agent.process_task(task)

    assert result is not None
    assert "status" in result

@pytest.mark.asyncio
async def test_system_expert_agent_clarification():
    agent = SystemExpertAgent()
    # 模糊问题，应该触发澄清
    task = {"query": "系统报错了"}
    result = await agent.process_task(task)

    assert result is not None
    assert result.get("status") in ["clarification_requested", "success", "error"]
