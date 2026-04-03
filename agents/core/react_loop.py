"""
ReAct 循环模块
实现 Think-Act-Observe 的 Agent 主循环，与具体 Agent 类解耦。
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from utils.utils import strip_think, extract_think_blocks

logger = logging.getLogger(__name__)


class LoopExitReason(str, Enum):
    DONE           = "done"           # LLM returned no tool calls → clean finish
    MAX_ITERATIONS = "max_iterations" # hit the iteration cap
    LLM_ERROR      = "llm_error"      # LLM returned finish_reason == "error"


@dataclass
class LoopResult:
    content:         str
    tools_used:      List[str]
    messages:        List[Dict[str, Any]]
    reasoning_trace: List[str]
    exit_reason:     LoopExitReason
    iterations:      int


@dataclass
class LoopEvent:
    """A single streaming event emitted by run_agent_loop_stream."""
    event: str   # "reasoning" | "tool_call" | "done" | "error"
    data:  Dict[str, Any]


async def run_agent_loop(
    initial_messages: List[Dict[str, Any]],
    *,
    llm: Any,
    tools: Any,           # core.registry.ToolRegistry
    context: Any,         # core.context.ContextBuilder
    model: str,
    max_iterations: int = 40,
) -> LoopResult:
    """
    执行 Agent 的 ReAct（Think-Act-Observe）主循环。

    Returns:
        LoopResult with exit_reason set to one of:
          - DONE: LLM returned no tool calls (clean finish)
          - MAX_ITERATIONS: hit the iteration cap
          - LLM_ERROR: LLM returned finish_reason == "error"
    """
    messages = initial_messages.copy()
    tools_used: List[str] = []
    reasoning_trace: List[str] = []

    for iteration in range(1, max_iterations + 1):
        # ---- 1. 调用 LLM ----
        response = await llm.chat_with_retry(
            messages=messages,
            tools=tools.get_definitions(),
            model=model,
            reasoning_effort="high",
            include_reasoning=True,
            thinking={"type": "enabled"},
        )

        if response.finish_reason == "error":
            return LoopResult(
                content=response.content or "Error calling AI model.",
                tools_used=tools_used,
                messages=messages,
                reasoning_trace=reasoning_trace,
                exit_reason=LoopExitReason.LLM_ERROR,
                iterations=iteration,
            )

        # ---- 2. 提取推理内容 ----
        clean_content = strip_think(response.content)
        reasoning_parts: List[str] = []

        if response.reasoning_content:
            reasoning_parts.append(str(response.reasoning_content).strip())

        for block in (response.thinking_blocks or []):
            if isinstance(block, dict):
                value = block.get("text") or block.get("content") or block.get("reasoning")
                if value:
                    reasoning_parts.append(str(value).strip())
            elif block:
                reasoning_parts.append(str(block).strip())

        reasoning_parts.extend(extract_think_blocks(response.content))
        merged = "\n".join(p for p in reasoning_parts if p)
        if merged:
            reasoning_trace.append(merged)

        # ---- 3. 将 Assistant 消息追加到历史 ----
        tool_call_dicts: List[Dict[str, Any]] = []
        if response.has_tool_calls:
            for tc in response.tool_calls:
                if hasattr(tc, "model_dump"):
                    tool_call_dicts.append(tc.model_dump())
                elif isinstance(tc, dict):
                    tool_call_dicts.append(tc)
                else:
                    tool_call_dicts.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    })

        messages = context.add_assistant_message(
            messages,
            clean_content,
            tool_call_dicts or None,
            reasoning_content=response.reasoning_content,
            thinking_blocks=response.thinking_blocks,
        )

        # ---- 4. 工具调用 or 结束 ----
        if not response.has_tool_calls:
            return LoopResult(
                content=clean_content,
                tools_used=tools_used,
                messages=messages,
                reasoning_trace=reasoning_trace,
                exit_reason=LoopExitReason.DONE,
                iterations=iteration,
            )

        for tool_call in response.tool_calls:
            if isinstance(tool_call, dict):
                tc_name = tool_call["function"]["name"]
                tc_args = tool_call["function"]["arguments"]
                tc_id   = tool_call["id"]
            else:
                tc_name = tool_call.function.name
                tc_args = tool_call.function.arguments
                tc_id   = tool_call.id

            tools_used.append(tc_name)
            try:
                args = json.loads(tc_args) if isinstance(tc_args, str) else tc_args
            except json.JSONDecodeError:
                args = {}

            logger.info("Tool call: %s", tc_name)
            result = await tools.execute(tc_name, args)
            messages = context.add_tool_result(messages, tc_id, tc_name, result)

    # Loop exhausted — MAX_ITERATIONS
    return LoopResult(
        content="Max iterations reached without completion.",
        tools_used=tools_used,
        messages=messages,
        reasoning_trace=reasoning_trace,
        exit_reason=LoopExitReason.MAX_ITERATIONS,
        iterations=max_iterations,
    )


async def run_agent_loop_stream(
    initial_messages: List[Dict[str, Any]],
    *,
    llm: Any,
    tools: Any,
    context: Any,
    model: str,
    max_iterations: int = 40,
) -> AsyncGenerator[LoopEvent, None]:
    """
    Streaming variant of run_agent_loop.
    Yields LoopEvent as reasoning steps, tool calls, and the final answer arrive,
    so the caller can forward them to the client in real time.

    Event types emitted:
      status     — stage progress updates (thinking, tool_executing, observing, etc.)
      reasoning  — LLM reasoning/thinking chunks (streamed in real time)
      tool_call  — before a tool is executed
      tool_result — after a tool execution completes
      done       — final answer
      error      — unrecoverable failure
    """
    import time as _time

    messages = initial_messages.copy()
    tools_used: List[str] = []
    reasoning_trace: List[str] = []

    for iteration in range(1, max_iterations + 1):
        # ---- 1. 通知客户端：正在进行 LLM 推理 ----
        yield LoopEvent(
            event="status",
            data={
                "stage": "thinking",
                "message": f"正在思考（第 {iteration} 步）…",
                "iteration": iteration,
                "max_iterations": max_iterations,
            },
        )

        # ---- 2. 流式调用 LLM，实时 yield 推理 token ----
        step_reasoning_parts: List[str] = []
        response: Optional[Any] = None
        llm_start = _time.monotonic()

        # State for <think>...</think> block parsing in content tokens
        _in_think   = False
        _think_buf  = ""

        async for chunk_type, chunk_data in llm.chat_with_retry_stream(
            messages=messages,
            tools=tools.get_definitions(),
            model=model,
            reasoning_effort="high",
            include_reasoning=True,
            thinking={"type": "enabled"},
        ):
            if chunk_type == "reasoning":
                # Models that natively stream reasoning_content (e.g. DeepSeek R1)
                step_reasoning_parts.append(chunk_data)
                yield LoopEvent(
                    event="reasoning",
                    data={"step": iteration, "content": chunk_data, "partial": True},
                )

            elif chunk_type == "content_delta":
                # Parse <think>...</think> blocks in real time for models that embed
                # thinking inside content (e.g. Qwen, Ollama models with thinking enabled)
                text = chunk_data
                while text:
                    if _in_think:
                        end_idx = text.find("</think>")
                        if end_idx >= 0:
                            fragment = text[:end_idx]
                            if fragment:
                                step_reasoning_parts.append(fragment)
                                yield LoopEvent(
                                    event="reasoning",
                                    data={"step": iteration, "content": fragment, "partial": True},
                                )
                            _in_think = False
                            _think_buf = ""
                            text = text[end_idx + 8:]  # len("</think>") == 8
                        else:
                            step_reasoning_parts.append(text)
                            yield LoopEvent(
                                event="reasoning",
                                data={"step": iteration, "content": text, "partial": True},
                            )
                            text = ""
                    else:
                        start_idx = text.find("<think>")
                        if start_idx >= 0:
                            # Emit any answer content that precedes the <think> block
                            pre_think = text[:start_idx]
                            if pre_think:
                                yield LoopEvent(
                                    event="answer_delta",
                                    data={"content": pre_think, "partial": True},
                                )
                            _in_think = True
                            text = text[start_idx + 7:]  # len("<think>") == 7
                        else:
                            # Final-answer tokens — stream them to the client in real time
                            yield LoopEvent(
                                event="answer_delta",
                                data={"content": text, "partial": True},
                            )
                            text = ""

            elif chunk_type == "done":
                response = chunk_data

        if response is None:
            yield LoopEvent(event="error", data={"message": "LLM 未返回响应"})
            return

        llm_elapsed_ms = int((_time.monotonic() - llm_start) * 1000)

        if response.finish_reason == "error":
            yield LoopEvent(event="error", data={"message": response.content or "LLM error"})
            return

        # ---- 3. 合并推理内容（streaming 已逐块 yield，此处仅汇总 trace）----
        clean_content = strip_think(response.content)
        reasoning_parts: List[str] = list(step_reasoning_parts)

        # 兜底：从整体 response 字段获取推理（非流式模型）
        if not reasoning_parts:
            if response.reasoning_content:
                reasoning_parts.append(str(response.reasoning_content).strip())
            for block in (response.thinking_blocks or []):
                if isinstance(block, dict):
                    value = block.get("text") or block.get("content") or block.get("reasoning")
                    if value:
                        reasoning_parts.append(str(value).strip())
                elif block:
                    reasoning_parts.append(str(block).strip())
            reasoning_parts.extend(extract_think_blocks(response.content or ""))

            # 对于非流式推理模型，补发一次完整 reasoning 事件
            merged_fallback = "\n".join(p for p in reasoning_parts if p)
            if merged_fallback:
                yield LoopEvent(
                    event="reasoning",
                    data={"step": iteration, "content": merged_fallback, "partial": False},
                )

        merged = "\n".join(p for p in reasoning_parts if p)
        if merged:
            reasoning_trace.append(merged)

        yield LoopEvent(
            event="status",
            data={
                "stage": "thinking_done",
                "message": f"第 {iteration} 步推理完成（耗时 {llm_elapsed_ms} ms）",
                "iteration": iteration,
                "llm_elapsed_ms": llm_elapsed_ms,
            },
        )

        # ---- 4. 将 Assistant 消息追加到历史 ----
        tool_call_dicts: List[Dict[str, Any]] = []
        if response.has_tool_calls:
            for tc in response.tool_calls:
                if hasattr(tc, "model_dump"):
                    tool_call_dicts.append(tc.model_dump())
                elif isinstance(tc, dict):
                    tool_call_dicts.append(tc)
                else:
                    tool_call_dicts.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    })

        messages = context.add_assistant_message(
            messages,
            clean_content,
            tool_call_dicts or None,
            reasoning_content=response.reasoning_content,
            thinking_blocks=response.thinking_blocks,
        )

        # ---- 5. 工具调用 or 结束 ----
        if not response.has_tool_calls:
            yield LoopEvent(
                event="done",
                data={
                    "content": clean_content,
                    "tools_used": tools_used,
                    "messages": messages,
                    "reasoning_trace": reasoning_trace,
                    "exit_reason": LoopExitReason.DONE.value,
                    "iterations": iteration,
                },
            )
            return

        for tool_call in response.tool_calls:
            if isinstance(tool_call, dict):
                tc_name = tool_call["function"]["name"]
                tc_args = tool_call["function"]["arguments"]
                tc_id   = tool_call["id"]
            else:
                tc_name = tool_call.function.name
                tc_args = tool_call.function.arguments
                tc_id   = tool_call.id

            tools_used.append(tc_name)
            try:
                args = json.loads(tc_args) if isinstance(tc_args, str) else tc_args
            except json.JSONDecodeError:
                args = {}

            yield LoopEvent(
                event="tool_call",
                data={"name": tc_name, "iteration": iteration},
            )
            logger.info("Tool call: %s", tc_name)
            tool_start = _time.monotonic()
            result = await tools.execute(tc_name, args)
            tool_elapsed_ms = int((_time.monotonic() - tool_start) * 1000)

            yield LoopEvent(
                event="tool_result",
                data={
                    "name": tc_name,
                    "iteration": iteration,
                    "elapsed_ms": tool_elapsed_ms,
                    "success": not (isinstance(result, str) and result.startswith("Error")),
                },
            )

            yield LoopEvent(
                event="status",
                data={
                    "stage": "observing",
                    "message": f"工具 {tc_name} 执行完毕，正在观察结果…",
                    "iteration": iteration,
                },
            )

            messages = context.add_tool_result(messages, tc_id, tc_name, result)

    # Loop exhausted — MAX_ITERATIONS
    yield LoopEvent(
        event="done",
        data={
            "content": "Max iterations reached without completion.",
            "tools_used": tools_used,
            "messages": messages,
            "reasoning_trace": reasoning_trace,
            "exit_reason": LoopExitReason.MAX_ITERATIONS.value,
            "iterations": max_iterations,
        },
    )
