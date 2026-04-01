from core.react_loop import LoopExitReason, LoopResult


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
