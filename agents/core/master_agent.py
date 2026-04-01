"""
MasterAgent 主智能体模块
负责协调会话管理、请求路由和 ReAct 循环执行。
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.monitor import AgentMonitor
from core.protocol import AgentRequest, AgentResponse
from core.llm import llm_service
from core.session import SessionManager, Session
from core.context import ContextBuilder
from core.memory import MemoryConsolidator
from core.registry import ToolRegistry
from core.router import AgentRouter
from core.react_loop import run_agent_loop
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

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        处理统一的 Agent 请求。

        流程：
          1. 获取或创建会话
          2. 构建消息上下文
          3. 尝试路由到子 Agent（快速匹配 → LLM 推断）
          4. 若无路由命中，执行 MasterAgent 自身的 ReAct 循环
          5. 持久化新产生的对话轮次
        """
        start_time = time.time()
        try:
            # 1. 会话
            session = self.session_manager.get_or_create(str(request.session_id))
            session.add_message("user", request.query)

            # 2. 构建初始消息列表
            all_history = session.get_history()
            initial_messages = self.context.build_messages(
                history=all_history[:-1],
                current_message=request.query,
                channel="master",
                chat_id=request.session_id,
            )
            self._inject_reasoning_prompt(initial_messages)

            # 3. 路由解析（同步快速匹配）
            target_agent, route_source, resolved_purpose = self.router.resolve_route_target(
                request.query, request.parameters
            )
            resolved_confidence: Optional[float] = None

            # 4. 若快速匹配无结果，尝试 LLM 推断
            if not target_agent:
                inferred = await self.router.infer_purpose_with_llm(
                    request.query, request.parameters
                )
                if inferred:
                    from core.router import _PURPOSE_AGENT_MAP
                    target_agent = _PURPOSE_AGENT_MAP[inferred["purpose"]]
                    route_source = "purpose_inferred_llm"
                    resolved_purpose = inferred["purpose"]
                    resolved_confidence = inferred["confidence"]

            # 5. 委托给子 Agent
            if target_agent:
                routed = await self._delegate_to_agent(
                    request, session, target_agent,
                    route_source, resolved_purpose, resolved_confidence, start_time,
                )
                if routed is not None:
                    return routed

            # 6. MasterAgent 自身 ReAct 循环
            effective_model = (
                request.parameters.get("model_version")
                if isinstance(request.parameters, dict) else None
            ) or self.model_name

            final_content, tools_used, full_history, reasoning_trace = await run_agent_loop(
                initial_messages,
                llm=self.llm,
                tools=self.tools,
                context=self.context,
                model=effective_model,
                max_iterations=self.max_iterations,
            )

            # 7. 持久化新产生的对话轮次
            for msg in full_history[len(initial_messages):]:
                if "timestamp" not in msg:
                    msg["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                session.messages.append(msg)
            session.updated_at = datetime.now()
            self.session_manager.save(session)

            return AgentResponse(
                answer=final_content or "No response generated.",
                source_agent="master_agent",
                latency_ms=(time.time() - start_time) * 1000,
                metadata={
                    "tools_used": tools_used,
                    "iteration_count": len(full_history),
                    "reasoning_trace": reasoning_trace,
                },
            )

        except Exception as e:
            logger.error("MasterAgent process failed: %s", e, exc_info=True)
            return AgentResponse(
                answer="An internal error occurred.",
                source_agent="system",
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )

    async def _delegate_to_agent(
        self,
        request: AgentRequest,
        session: Session,
        target_agent: str,
        route_source: Optional[str],
        resolved_purpose: Optional[str],
        resolved_confidence: Optional[float],
        start_time: float,
    ) -> Optional[AgentResponse]:
        """将请求委托给子 Agent 并返回标准响应。委托失败时返回 None，让调用方回退到 ReAct 循环。"""
        try:
            agent_instance = self.router.get_or_create_agent(target_agent)
            if agent_instance is None:
                logger.warning("Delegated agent not found: %s", target_agent)
                return None

            task = self.router.build_task_for_agent(target_agent, request)
            result = await agent_instance.execute(task)
            answer = self.router.extract_answer_from_agent_result(result) or "No response generated."

            session.add_message("assistant", answer)
            session.updated_at = datetime.now()
            self.session_manager.save(session)

            purpose = resolved_purpose or (
                request.parameters.get("purpose")
                if isinstance(request.parameters, dict) else None
            )
            return AgentResponse(
                answer=answer,
                source_agent=target_agent,
                latency_ms=(time.time() - start_time) * 1000,
                metadata={
                    "routing": {
                        "mode": "delegated_agent",
                        "source": route_source,
                        "target_agent": target_agent,
                        "purpose": purpose,
                        "confidence": resolved_confidence,
                    },
                    "delegated_task": task,
                    "delegated_result": result,
                },
            )
        except Exception as exc:
            logger.error("Delegation failed for %s: %s", target_agent, exc, exc_info=True)
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
