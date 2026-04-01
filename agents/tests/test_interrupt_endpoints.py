import pytest
import os
import asyncio
import agents
print("AGENTS MODULE:", agents.__file__)


from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.interrupt_endpoints import router as interrupt_router

app = FastAPI()
app.include_router(interrupt_router, prefix="/api")

client = TestClient(app)


@pytest.mark.asyncio
async def test_interrupt_endpoints():
    thread_id = "test_thread_endpoint"

    # Mock the graph's _call_model to return a tool call that triggers interrupt
    from agents.comprehensive_demo_agent.graph import ComprehensiveDemoAgent
    from langchain_core.messages import AIMessage

    original_call_model = ComprehensiveDemoAgent._call_model

    async def mock_call_model(self, state):
        ai_message = AIMessage(
            content="",
            tool_calls=[{"name": "file_operation", "args": {"action": "write", "path": "test.txt", "content": "hello"}, "id": "call_123"}]
        )
        return {
            "messages": [ai_message],
            "requires_user_input": True,
            "error": None
        }

    ComprehensiveDemoAgent._call_model = mock_call_model

    try:
        # 1. 启动 Agent，触发文件写入中断
        start_payload = {
            "agent_id": "comprehensive_demo_agent",
            "thread_id": thread_id,
            "input_data": {
                "messages": [("user", "将hello world写入test.txt")]
            }
        }

        start_response = client.post("/api/v1/agents/start", json=start_payload)
        assert start_response.status_code == 200
        start_data = start_response.json()
        print("START DATA:", start_data)
        assert start_data["status"] == "interrupted"
        assert "human_review" in start_data["pending_nodes"]

        # 2. 查询状态
        status_response = client.get(f"/api/v1/agents/comprehensive_demo_agent/status/{thread_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "interrupted"
        assert "human_review" in status_data["pending_nodes"]

        # 3. 恢复 Agent (确认操作)
        resume_payload = {
            "agent_id": "comprehensive_demo_agent",
            "thread_id": thread_id,
            "user_feedback": {"requires_user_input": False}
        }
        resume_response = client.post("/api/v1/agents/resume", json=resume_payload)
        assert resume_response.status_code == 200
        resume_data = resume_response.json()

        # 因为继续执行后可能会返回完成状态
        assert resume_data["status"] == "completed" or resume_data["status"] == "interrupted"
    finally:
        ComprehensiveDemoAgent._call_model = original_call_model


@pytest.mark.asyncio
async def test_interrupt_endpoints_errors():
    # 1. Start unknown agent
    start_payload = {
        "agent_id": "unknown_agent_123",
        "thread_id": "test_thread",
        "input_data": {}
    }
    response = client.post("/api/v1/agents/start", json=start_payload)
    assert response.status_code == 404

    # 2. Get status of unknown agent
    response = client.get("/api/v1/agents/unknown_agent_123/status/test_thread")
    assert response.status_code == 404

    # 3. Resume unknown agent
    resume_payload = {
        "agent_id": "unknown_agent_123",
        "thread_id": "test_thread",
        "user_feedback": {}
    }
    response = client.post("/api/v1/agents/resume", json=resume_payload)
    assert response.status_code == 404

    # 4. Get status of non-existent thread for valid agent
    response = client.get("/api/v1/agents/comprehensive_demo_agent/status/non_existent_thread_123")
    assert response.status_code == 404

    # 5. Resume non-interrupted agent
    resume_payload = {
        "agent_id": "comprehensive_demo_agent",
        "thread_id": "non_existent_thread_123",
        "user_feedback": {}
    }
    response = client.post("/api/v1/agents/resume", json=resume_payload)
    assert response.status_code == 400
