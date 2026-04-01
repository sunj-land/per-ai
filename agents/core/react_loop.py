"""
ReAct 循环模块
实现 Think-Act-Observe 的 Agent 主循环，与具体 Agent 类解耦。
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

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
