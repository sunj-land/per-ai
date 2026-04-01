import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from core.master_agent import MasterAgent
from core.protocol import AgentRequest, AgentResponse
from core.react_loop import LoopResult, LoopExitReason
from core.router import RouteResult


def make_agent():
    with patch("core.master_agent.ensure_dir"), \
         patch("core.master_agent.SessionManager"), \
         patch("core.master_agent.ContextBuilder"), \
         patch("core.master_agent.ToolRegistry"), \
         patch("core.master_agent.MemoryConsolidator"), \
         patch("core.master_agent.AgentRouter"), \
         patch("core.master_agent.llm_service"):
        agent = MasterAgent(model_name="test-model")
    return agent


def test_setup_session_returns_session_and_messages():
    agent = make_agent()
    session = MagicMock()
    agent.session_manager.get_or_create.return_value = session
    session.get_history.return_value = [{"role": "user", "content": "hi"}]
    agent.context.build_messages.return_value = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]

    request = AgentRequest(query="hi", session_id="s1")
    result_session, messages = agent._setup_session(request)

    assert result_session is session
    session.add_message.assert_called_once_with("user", "hi")
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"


def test_route_request_delegates_to_router():
    agent = make_agent()
    expected = RouteResult(target_agent="text_agent", source="keyword", purpose="text_summarize", confidence=None)
    agent.router.resolve = AsyncMock(return_value=expected)

    request = AgentRequest(query="summarize this", session_id="s1")
    result = asyncio.run(agent._route_request(request))

    agent.router.resolve.assert_called_once_with("summarize this", request.parameters)
    assert result is expected


def test_run_react_loop_returns_loop_result():
    agent = make_agent()
    loop_result = LoopResult(
        content="answer",
        tools_used=[],
        messages=[],
        reasoning_trace=[],
        exit_reason=LoopExitReason.DONE,
        iterations=1,
    )

    with patch("core.master_agent.run_agent_loop", new=AsyncMock(return_value=loop_result)):
        request = AgentRequest(query="test", session_id="s1")
        messages = [{"role": "user", "content": "test"}]
        result = asyncio.run(agent._run_react_loop(request, messages))

    assert result is loop_result


def test_persist_and_respond_saves_session_and_returns_response():
    agent = make_agent()
    session = MagicMock()
    session.messages = []
    loop_result = LoopResult(
        content="final answer",
        tools_used=["read_file"],
        messages=[
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "final answer"},
        ],
        reasoning_trace=["thought"],
        exit_reason=LoopExitReason.DONE,
        iterations=2,
    )

    request = AgentRequest(query="q", session_id="s1")
    response = agent._persist_and_respond(request, session, loop_result, time.time())

    agent.session_manager.save.assert_called_once_with(session)
    assert isinstance(response, AgentResponse)
    assert response.answer == "final answer"
    assert response.source_agent == "master_agent"
    assert response.metadata["exit_reason"] == "done"
    assert response.metadata["tools_used"] == ["read_file"]


def test_process_request_uses_helpers_in_order():
    agent = make_agent()

    session = MagicMock()
    session.messages = []
    messages = [{"role": "user", "content": "hi"}]
    route = RouteResult(None, None, None, None)
    loop_result = LoopResult(
        content="hi back",
        tools_used=[],
        messages=messages,
        reasoning_trace=[],
        exit_reason=LoopExitReason.DONE,
        iterations=1,
    )

    agent._setup_session = MagicMock(return_value=(session, messages))
    agent._route_request = AsyncMock(return_value=route)
    agent._run_react_loop = AsyncMock(return_value=loop_result)
    agent._persist_and_respond = MagicMock(return_value=AgentResponse(
        answer="hi back", source_agent="master_agent", latency_ms=10.0
    ))

    request = AgentRequest(query="hi", session_id="s1")
    response = asyncio.run(agent.process_request(request))

    agent._setup_session.assert_called_once_with(request)
    agent._route_request.assert_called_once_with(request)
    agent._run_react_loop.assert_called_once_with(request, messages)
    agent._persist_and_respond.assert_called_once()
    assert response.answer == "hi back"
