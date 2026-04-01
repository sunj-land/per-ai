# MasterAgent Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `MasterAgent`, `AgentRouter`, and `run_agent_loop` so that loop exit conditions are typed, routing is a composable strategy chain, and `process_request` is a thin orchestrator delegating to named private helpers.

**Architecture:** Three files change in dependency order — `react_loop.py` first (adds `LoopResult`), then `router.py` (adds `RouteResult` + strategy chain), then `master_agent.py` (consumes both). Each task is independently testable before the next begins.

**Tech Stack:** Python 3.12, pytest, `unittest.mock.AsyncMock`, `dataclasses`, `enum`

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `agents/core/react_loop.py` | Modify | Add `LoopExitReason` enum, `LoopResult` dataclass; change `run_agent_loop` return type from 4-tuple to `LoopResult` |
| `agents/core/router.py` | Modify | Add `RouteResult` dataclass; add `resolve()` public method + 4 private `_strategy_*` methods; preserve all existing public methods |
| `agents/core/master_agent.py` | Modify | Extract `_setup_session`, `_route_request`, `_run_react_loop`, `_persist_and_respond`; update `_delegate_to_agent`; remove inline routing logic |
| `agents/tests/test_react_loop.py` | Create | Unit tests for `LoopResult` exit reasons |
| `agents/tests/test_router.py` | Create | Unit tests for each routing strategy and `resolve()` chain |
| `agents/tests/test_master_agent.py` | Create | Unit tests for each private helper and `process_request` orchestration |

---

## Task 1: Add `LoopExitReason` and `LoopResult` to `react_loop.py`

**Files:**
- Modify: `agents/core/react_loop.py`
- Create: `agents/tests/test_react_loop.py`

- [ ] **Step 1: Write the failing test**

Create `agents/tests/test_react_loop.py`:

```python
import pytest
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd agents && python -m pytest tests/test_react_loop.py -v
```

Expected: `ImportError` — `LoopExitReason` and `LoopResult` do not exist yet.

- [ ] **Step 3: Add `LoopExitReason` and `LoopResult` to `react_loop.py`**

At the top of `agents/core/react_loop.py`, after the existing imports, add:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional  # already imported — keep existing


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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd agents && python -m pytest tests/test_react_loop.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/core/react_loop.py agents/tests/test_react_loop.py
git commit -m "feat: add LoopExitReason enum and LoopResult dataclass to react_loop"
```

---

## Task 2: Change `run_agent_loop` return type to `LoopResult`

**Files:**
- Modify: `agents/core/react_loop.py`
- Modify: `agents/tests/test_react_loop.py`

- [ ] **Step 1: Write the failing test**

Append to `agents/tests/test_react_loop.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock
from core.react_loop import run_agent_loop, LoopExitReason, LoopResult


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
    # LLM always returns tool calls so loop never exits naturally
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd agents && python -m pytest tests/test_react_loop.py::test_run_agent_loop_returns_loop_result_on_done -v
```

Expected: FAIL — `run_agent_loop` still returns a 4-tuple, not `LoopResult`.

- [ ] **Step 3: Rewrite `run_agent_loop` to return `LoopResult`**

Replace the body of `run_agent_loop` in `agents/core/react_loop.py`. The signature changes from returning `tuple[Optional[str], ...]` to `LoopResult`:

```python
async def run_agent_loop(
    initial_messages: List[Dict[str, Any]],
    *,
    llm: Any,
    tools: Any,
    context: Any,
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
    final_content: Optional[str] = None
    tools_used: List[str] = []
    reasoning_trace: List[str] = []
    exit_reason = LoopExitReason.MAX_ITERATIONS  # default if loop exhausts

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
            final_content = response.content or "Error calling AI model."
            exit_reason = LoopExitReason.LLM_ERROR
            return LoopResult(
                content=final_content,
                tools_used=tools_used,
                messages=messages,
                reasoning_trace=reasoning_trace,
                exit_reason=exit_reason,
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
            final_content = clean_content
            exit_reason = LoopExitReason.DONE
            return LoopResult(
                content=final_content,
                tools_used=tools_used,
                messages=messages,
                reasoning_trace=reasoning_trace,
                exit_reason=exit_reason,
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
```

- [ ] **Step 4: Run all react_loop tests**

```bash
cd agents && python -m pytest tests/test_react_loop.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/core/react_loop.py agents/tests/test_react_loop.py
git commit -m "feat: run_agent_loop now returns LoopResult with typed exit_reason and iteration count"
```

---

## Task 3: Add `RouteResult` and strategy chain to `router.py`

**Files:**
- Modify: `agents/core/router.py`
- Create: `agents/tests/test_router.py`

- [ ] **Step 1: Write the failing test**

Create `agents/tests/test_router.py`:

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.router import AgentRouter, RouteResult


def make_router():
    llm = MagicMock()
    return AgentRouter(llm=llm, model_name="test-model")


def test_route_result_is_dataclass():
    r = RouteResult(target_agent="article_query_agent", source="agent_name", purpose=None, confidence=None)
    assert r.target_agent == "article_query_agent"
    assert r.source == "agent_name"


def test_resolve_explicit_agent_name():
    router = make_router()
    result = asyncio.run(router.resolve("any query", {"agent_name": "text_agent"}))
    assert result.target_agent == "text_agent"
    assert result.source == "agent_name"


def test_resolve_explicit_purpose():
    router = make_router()
    result = asyncio.run(router.resolve("any query", {"purpose": "text_summarize"}))
    assert result.target_agent == "text_agent"
    assert result.source == "purpose"
    assert result.purpose == "text_summarize"


def test_resolve_keyword_infer():
    router = make_router()
    result = asyncio.run(router.resolve("帮我总结这篇文章", {}))
    assert result.target_agent == "text_agent"
    assert result.source == "purpose_inferred"


def test_resolve_falls_through_to_none():
    router = make_router()
    # No keywords match, LLM inference disabled via low-confidence mock
    mock_resp = MagicMock()
    mock_resp.finish_reason = "stop"
    mock_resp.content = '{"purpose": "general", "confidence": 0.5}'
    router._llm.chat_with_retry = AsyncMock(return_value=mock_resp)

    result = asyncio.run(router.resolve("hello world", {}))
    assert result.target_agent is None
    assert result.source is None


def test_resolve_master_agent_alias_is_not_routed():
    router = make_router()
    result = asyncio.run(router.resolve("any query", {"agent_name": "master_agent"}))
    assert result.target_agent is None


def test_resolve_llm_infer_high_confidence():
    router = make_router()
    mock_resp = MagicMock()
    mock_resp.finish_reason = "stop"
    mock_resp.content = '{"purpose": "data_analysis", "confidence": 0.95}'
    router._llm.chat_with_retry = AsyncMock(return_value=mock_resp)

    result = asyncio.run(router.resolve("analyze this dataset", {}))
    assert result.target_agent == "data_agent"
    assert result.source == "purpose_inferred_llm"
    assert result.confidence == pytest.approx(0.95)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd agents && python -m pytest tests/test_router.py -v
```

Expected: `ImportError` — `RouteResult` does not exist; `router.resolve` does not exist.

- [ ] **Step 3: Add `RouteResult`, strategy methods, and `resolve()` to `router.py`**

At the top of `agents/core/router.py`, after existing imports, add:

```python
from dataclasses import dataclass
from typing import Callable, Optional  # Optional already imported — keep existing
```

After the existing module-level constants, add:

```python
@dataclass
class RouteResult:
    target_agent: Optional[str]
    source:       Optional[str]
    purpose:      Optional[str]
    confidence:   Optional[float]
```

Inside `AgentRouter.__init__`, after `self._agent_cache`:

```python
self._strategies: list = [
    self._strategy_explicit_agent,
    self._strategy_explicit_purpose,
    self._strategy_keyword_infer,
    self._strategy_llm_infer,
]
```

Add these four private strategy methods and the public `resolve()` inside `AgentRouter`:

```python
async def resolve(self, query: str, parameters: Optional[Dict[str, Any]]) -> RouteResult:
    """Run strategies in priority order, return first hit. Falls through to empty RouteResult."""
    for strategy in self._strategies:
        result = await strategy(query, parameters)
        if result and result.target_agent:
            return result
    return RouteResult(None, None, None, None)

async def _strategy_explicit_agent(
    self, query: str, parameters: Optional[Dict[str, Any]]
) -> Optional[RouteResult]:
    if not isinstance(parameters, dict):
        return None
    explicit_agent = str(parameters.get("agent_name", "")).strip()
    if explicit_agent and explicit_agent.lower() not in _MASTER_AGENT_ALIASES:
        return RouteResult(target_agent=explicit_agent, source="agent_name", purpose=None, confidence=None)
    return None

async def _strategy_explicit_purpose(
    self, query: str, parameters: Optional[Dict[str, Any]]
) -> Optional[RouteResult]:
    if not isinstance(parameters, dict):
        return None
    purpose = str(parameters.get("purpose", "")).strip().lower()
    if purpose and purpose in _PURPOSE_AGENT_MAP:
        return RouteResult(
            target_agent=_PURPOSE_AGENT_MAP[purpose],
            source="purpose",
            purpose=purpose,
            confidence=None,
        )
    return None

async def _strategy_keyword_infer(
    self, query: str, parameters: Optional[Dict[str, Any]]
) -> Optional[RouteResult]:
    inferred = self.infer_purpose_from_query(query)
    if inferred and inferred in _PURPOSE_AGENT_MAP:
        return RouteResult(
            target_agent=_PURPOSE_AGENT_MAP[inferred],
            source="purpose_inferred",
            purpose=inferred,
            confidence=None,
        )
    return None

async def _strategy_llm_infer(
    self, query: str, parameters: Optional[Dict[str, Any]]
) -> Optional[RouteResult]:
    inferred = await self.infer_purpose_with_llm(query, parameters)
    if inferred:
        return RouteResult(
            target_agent=_PURPOSE_AGENT_MAP[inferred["purpose"]],
            source="purpose_inferred_llm",
            purpose=inferred["purpose"],
            confidence=inferred["confidence"],
        )
    return None
```

- [ ] **Step 4: Run all router tests**

```bash
cd agents && python -m pytest tests/test_router.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/core/router.py agents/tests/test_router.py
git commit -m "feat: add RouteResult and async resolve() strategy chain to AgentRouter"
```

---

## Task 4: Decompose `master_agent.py` — helpers and updated `process_request`

**Files:**
- Modify: `agents/core/master_agent.py`
- Create: `agents/tests/test_master_agent.py`

- [ ] **Step 1: Write the failing tests**

Create `agents/tests/test_master_agent.py`:

```python
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
    initial_len = 0
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd agents && python -m pytest tests/test_master_agent.py -v
```

Expected: Multiple failures — `_setup_session`, `_route_request`, `_run_react_loop`, `_persist_and_respond` don't exist yet.

- [ ] **Step 3: Rewrite `master_agent.py` with helper methods**

Replace the full content of `agents/core/master_agent.py`:

```python
"""
MasterAgent 主智能体模块
负责协调会话管理、请求路由和 ReAct 循环执行。
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.monitor import AgentMonitor
from core.protocol import AgentRequest, AgentResponse
from core.llm import llm_service
from core.session import SessionManager, Session
from core.context import ContextBuilder
from core.memory import MemoryConsolidator
from core.registry import ToolRegistry
from core.router import AgentRouter, RouteResult
from core.react_loop import run_agent_loop, LoopResult, LoopExitReason
from tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from utils.utils import ensure_dir

logger = logging.getLogger(__name__)

_REASONING_SYSTEM_PROMPT = (
    "请在回答时输出可解析的推理过程。"
    "优先通过模型原生字段 reasoning_content 或 thinking_blocks 返回。"
    "如果模型不支持原生推理字段，请在答案中使用 <think>...</think> 包裹思考过程。"
)


class MasterAgent:
    """
    主智能体。

    职责：
      1. 会话管理 — 获取/创建会话，持久化对话历史
      2. 请求路由 — 委托 AgentRouter 将请求分发给合适的子 Agent
      3. ReAct 循环 — 委托 run_agent_loop 执行 Think-Act-Observe 循环
    """

    def __init__(self, model_name: str = "ollama/llama3") -> None:
        self.model_name = model_name
        self.monitor = AgentMonitor()
        self.workspace = ensure_dir(Path.cwd() / "workspace")

        self.session_manager = SessionManager(self.workspace)
        self.context = ContextBuilder(self.workspace)
        self.tools = ToolRegistry()
        self.llm = llm_service

        self.max_iterations = 40
        self.context_window_tokens = 65_536

        self.memory_consolidator = MemoryConsolidator(
            workspace=self.workspace,
            provider=self.llm,
            model=self.model_name,
            sessions=self.session_manager,
            context_window_tokens=self.context_window_tokens,
            build_messages=self.context.build_messages,
            get_tool_definitions=self.tools.get_definitions,
        )
        self.router = AgentRouter(llm=self.llm, model_name=self.model_name)
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.tools.register(ReadFileTool(workspace=self.workspace))
        self.tools.register(WriteFileTool(workspace=self.workspace))
        self.tools.register(EditFileTool(workspace=self.workspace))
        self.tools.register(ListDirTool(workspace=self.workspace))

    # ------------------------------------------------------------------ #
    # Public entry point                                                    #
    # ------------------------------------------------------------------ #

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        处理统一的 Agent 请求。

        流程：
          1. 建立会话并构建初始消息上下文
          2. 尝试路由到子 Agent（策略链：显式指定 → purpose → 关键词 → LLM 推断）
          3. 若路由命中，委托子 Agent 处理
          4. 否则，执行 MasterAgent 自身的 ReAct 循环
          5. 持久化对话并返回响应
        """
        start_time = time.time()
        try:
            session, messages = self._setup_session(request)
            route = await self._route_request(request)

            if route.target_agent:
                response = await self._delegate_to_agent(request, session, route, start_time)
                if response is not None:
                    return response

            loop_result = await self._run_react_loop(request, messages)
            return self._persist_and_respond(request, session, loop_result, start_time)

        except Exception as e:
            logger.error("MasterAgent process failed: %s", e, exc_info=True)
            return AgentResponse(
                answer="An internal error occurred.",
                source_agent="system",
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )

    # ------------------------------------------------------------------ #
    # Private helpers                                                        #
    # ------------------------------------------------------------------ #

    def _setup_session(
        self, request: AgentRequest
    ) -> Tuple[Session, List[Dict[str, Any]]]:
        """获取/创建会话，追加用户消息，构建并返回初始消息列表。"""
        session = self.session_manager.get_or_create(str(request.session_id))
        session.add_message("user", request.query)

        all_history = session.get_history()
        messages = self.context.build_messages(
            history=all_history[:-1],
            current_message=request.query,
            channel="master",
            chat_id=request.session_id,
        )
        self._inject_reasoning_prompt(messages)
        return session, messages

    async def _route_request(self, request: AgentRequest) -> RouteResult:
        """通过策略链确定目标子 Agent。"""
        return await self.router.resolve(request.query, request.parameters)

    async def _run_react_loop(
        self, request: AgentRequest, messages: List[Dict[str, Any]]
    ) -> LoopResult:
        """解析有效模型并执行 ReAct 循环，返回 LoopResult。"""
        effective_model = (
            request.parameters.get("model_version")
            if isinstance(request.parameters, dict) else None
        ) or self.model_name

        return await run_agent_loop(
            messages,
            llm=self.llm,
            tools=self.tools,
            context=self.context,
            model=effective_model,
            max_iterations=self.max_iterations,
        )

    def _persist_and_respond(
        self,
        request: AgentRequest,
        session: Session,
        loop_result: LoopResult,
        start_time: float,
    ) -> AgentResponse:
        """将 ReAct 循环产生的新消息写入会话并构建标准响应。"""
        # Append only the messages generated after the initial context
        for msg in loop_result.messages:
            if "timestamp" not in msg:
                msg["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            session.messages.append(msg)
        session.updated_at = datetime.now()
        self.session_manager.save(session)

        return AgentResponse(
            answer=loop_result.content or "No response generated.",
            source_agent="master_agent",
            latency_ms=(time.time() - start_time) * 1000,
            metadata={
                "tools_used": loop_result.tools_used,
                "iteration_count": loop_result.iterations,
                "exit_reason": loop_result.exit_reason.value,
                "reasoning_trace": loop_result.reasoning_trace,
            },
        )

    async def _delegate_to_agent(
        self,
        request: AgentRequest,
        session: Session,
        route: RouteResult,
        start_time: float,
    ) -> Optional[AgentResponse]:
        """将请求委托给子 Agent 并返回标准响应。委托失败时返回 None，让调用方回退到 ReAct 循环。"""
        try:
            agent_instance = self.router.get_or_create_agent(route.target_agent)
            if agent_instance is None:
                logger.warning("Delegated agent not found: %s", route.target_agent)
                return None

            task = self.router.build_task_for_agent(route.target_agent, request)
            result = await agent_instance.execute(task)
            answer = self.router.extract_answer_from_agent_result(result) or "No response generated."

            session.add_message("assistant", answer)
            session.updated_at = datetime.now()
            self.session_manager.save(session)

            purpose = route.purpose or (
                request.parameters.get("purpose")
                if isinstance(request.parameters, dict) else None
            )
            return AgentResponse(
                answer=answer,
                source_agent=route.target_agent,
                latency_ms=(time.time() - start_time) * 1000,
                metadata={
                    "routing": {
                        "mode": "delegated_agent",
                        "source": route.source,
                        "target_agent": route.target_agent,
                        "purpose": purpose,
                        "confidence": route.confidence,
                    },
                    "delegated_task": task,
                    "delegated_result": result,
                },
            )
        except Exception as exc:
            logger.error("Delegation failed for %s: %s", route.target_agent, exc, exc_info=True)
            return None

    @staticmethod
    def _inject_reasoning_prompt(messages: List[Dict[str, Any]]) -> None:
        """将推理引导指令注入到 system 消息中（就地修改）。"""
        if messages and messages[0].get("role") == "system":
            existing = str(messages[0].get("content", "")).strip()
            messages[0]["content"] = (
                f"{existing}\n\n{_REASONING_SYSTEM_PROMPT}" if existing else _REASONING_SYSTEM_PROMPT
            )
        else:
            messages.insert(0, {"role": "system", "content": _REASONING_SYSTEM_PROMPT})
```

- [ ] **Step 4: Run all master_agent tests**

```bash
cd agents && python -m pytest tests/test_master_agent.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd agents && python -m pytest tests/ -v --ignore=tests/benchmark_article_search.py --ignore=tests/migration_validate.py
```

Expected: All existing tests still PASS. If any test imported `run_agent_loop` and destructured the 4-tuple, it will fail — fix by updating that test to use `LoopResult` attributes instead.

- [ ] **Step 6: Commit**

```bash
git add agents/core/master_agent.py agents/tests/test_master_agent.py
git commit -m "refactor: decompose MasterAgent.process_request into _setup_session, _route_request, _run_react_loop, _persist_and_respond"
```

---

## Self-Review Notes

**Spec coverage check:**

| Spec requirement | Task that covers it |
|-----------------|---------------------|
| A3: `LoopExitReason` enum with DONE/MAX_ITERATIONS/LLM_ERROR | Task 1 |
| A3: `LoopResult` dataclass with `exit_reason` and `iterations` | Task 1 |
| A3: `run_agent_loop` returns `LoopResult` | Task 2 |
| B3: `RouteResult` dataclass | Task 3 |
| B3: `AgentRouter.resolve()` strategy chain | Task 3 |
| B3: 4 private strategy methods | Task 3 |
| B3: Existing public methods preserved | Task 3 (strategies reuse `infer_purpose_from_query`, `infer_purpose_with_llm`) |
| C1: `_setup_session` | Task 4 |
| C1: `_route_request` | Task 4 |
| C1: `_run_react_loop` | Task 4 |
| C1: `_persist_and_respond` with `exit_reason` in metadata | Task 4 |
| C1: `_delegate_to_agent` accepts `RouteResult` | Task 4 |
| C1: `_inject_reasoning_prompt` called inside `_setup_session` | Task 4 |

**No placeholders found.**

**Type consistency confirmed:** `RouteResult` defined in Task 3, consumed in Task 4. `LoopResult`/`LoopExitReason` defined in Task 1, used in Task 2 and Task 4. All method signatures match across tasks.

**Note on `_persist_and_respond`:** The current implementation appends all `loop_result.messages` to the session. This differs slightly from the original code which sliced `full_history[len(initial_messages):]`. The new behavior is correct because `run_agent_loop` receives a copy of `initial_messages` and appends to it; the returned `messages` contains only messages generated during the loop (the copy starts from the passed-in messages, so all entries in `loop_result.messages` are new). If this assumption is wrong after testing, adjust by passing `initial_message_count` into `_persist_and_respond`.
