import asyncio
from unittest.mock import AsyncMock, MagicMock
from core.react_loop import run_agent_loop, LoopExitReason, LoopResult


def test_loop_result_exit_reason_done():
    result = LoopResult(
        content="hello",
        tools_used=[],
        messages=[],
        reasoning_trace=[],
        exit_reason=LoopExitReason.DONE,
        iterations=1,
    )
    assert result.exit_reason == LoopExitReason.DONE
    assert result.exit_reason == "done"


def test_loop_result_exit_reason_max_iterations():
    result = LoopResult(
        content="Max iterations reached without completion.",
        tools_used=[],
        messages=[],
        reasoning_trace=[],
        exit_reason=LoopExitReason.MAX_ITERATIONS,
        iterations=40,
    )
    assert result.exit_reason == LoopExitReason.MAX_ITERATIONS
    assert result.iterations == 40
    assert result.exit_reason == "max_iterations"


def test_loop_result_exit_reason_llm_error():
    result = LoopResult(
        content="Error calling AI model.",
        tools_used=[],
        messages=[],
        reasoning_trace=[],
        exit_reason=LoopExitReason.LLM_ERROR,
        iterations=1,
    )
    assert result.exit_reason == LoopExitReason.LLM_ERROR
    assert result.exit_reason == "llm_error"


def _make_llm_response(content="done", finish_reason="stop", has_tool_calls=False):
    resp = MagicMock()
    resp.content = content
    resp.finish_reason = finish_reason
    resp.has_tool_calls = has_tool_calls
    resp.tool_calls = []
    resp.reasoning_content = None
    resp.thinking_blocks = []
    return resp


def _make_tools():
    tools = MagicMock()
    tools.get_definitions.return_value = []
    return tools


def _make_context():
    ctx = MagicMock()
    ctx.add_assistant_message.side_effect = lambda msgs, *a, **kw: msgs + [{"role": "assistant", "content": a[0]}]
    ctx.add_tool_result.side_effect = lambda msgs, *a, **kw: msgs
    return ctx


def test_run_agent_loop_returns_loop_result_on_done():
    llm = MagicMock()
    llm.chat_with_retry = AsyncMock(return_value=_make_llm_response("answer", "stop"))
    tools = _make_tools()
    ctx = _make_context()

    result = asyncio.run(run_agent_loop(
        [{"role": "user", "content": "hi"}],
        llm=llm,
        tools=tools,
        context=ctx,
        model="test-model",
        max_iterations=5,
    ))

    assert isinstance(result, LoopResult)
    assert result.exit_reason == LoopExitReason.DONE
    assert result.content == "answer"
    assert result.iterations == 1


def test_run_agent_loop_returns_max_iterations_reason():
    tool_call = MagicMock()
    tool_call.function.name = "fake_tool"
    tool_call.function.arguments = "{}"
    tool_call.id = "tc1"

    resp_with_tool = _make_llm_response("thinking", "stop", has_tool_calls=True)
    resp_with_tool.tool_calls = [tool_call]

    llm = MagicMock()
    llm.chat_with_retry = AsyncMock(return_value=resp_with_tool)
    tools = _make_tools()
    tools.execute = AsyncMock(return_value="tool result")
    ctx = _make_context()

    result = asyncio.run(run_agent_loop(
        [{"role": "user", "content": "loop forever"}],
        llm=llm,
        tools=tools,
        context=ctx,
        model="test-model",
        max_iterations=3,
    ))

    assert isinstance(result, LoopResult)
    assert result.exit_reason == LoopExitReason.MAX_ITERATIONS
    assert result.iterations == 3


def test_run_agent_loop_returns_llm_error_reason():
    llm = MagicMock()
    llm.chat_with_retry = AsyncMock(return_value=_make_llm_response("err msg", "error"))
    tools = _make_tools()
    ctx = _make_context()

    result = asyncio.run(run_agent_loop(
        [{"role": "user", "content": "hi"}],
        llm=llm,
        tools=tools,
        context=ctx,
        model="test-model",
    ))

    assert isinstance(result, LoopResult)
    assert result.exit_reason == LoopExitReason.LLM_ERROR
    assert result.iterations == 1
    assert result.content == "err msg"
