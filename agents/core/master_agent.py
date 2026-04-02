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

            # Build reasoning trace from routing decision + any reasoning in the sub-agent result
            reasoning_trace: List[str] = []
            routing_step = f"路由至「{route.target_agent}」（策略：{route.source}"
            if route.confidence is not None:
                routing_step += f"，置信度：{round(route.confidence * 100)}%"
            if purpose:
                routing_step += f"，用途：{purpose}"
            routing_step += "）"
            reasoning_trace.append(routing_step)

            if isinstance(result, dict):
                sub_reasoning = result.get("reasoning") or result.get("reasoning_trace")
                if isinstance(sub_reasoning, list):
                    reasoning_trace.extend(
                        str(item).strip() for item in sub_reasoning if item and str(item).strip()
                    )
                elif isinstance(sub_reasoning, str) and sub_reasoning.strip():
                    reasoning_trace.append(sub_reasoning.strip())

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
                    "reasoning_trace": reasoning_trace,
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
