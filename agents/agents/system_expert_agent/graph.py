import json
import logging
from typing import Dict, Any, Literal

from langchain_core.messages import AIMessage, HumanMessage

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.llm import LLMService
from .state import SystemExpertState
from .tools import KnowledgeBaseTool
from .prompt import INTENT_ANALYSIS_PROMPT, CLARIFICATION_PROMPT, GENERATE_RESPONSE_PROMPT

logger = logging.getLogger(__name__)


def build_system_expert_graph(
    kb_tool: KnowledgeBaseTool,
    llm: LLMService,
    confidence_threshold: float = 0.7,
):
    """
    构建智能对话专家工作流（独立函数，可单独测试或复用）。

    :param kb_tool: 知识库检索工具
    :param llm: LLM 服务实例
    :param confidence_threshold: 触发澄清的置信度下限
    :return: 编译后的 CompiledStateGraph
    """

    def _route_after_analysis(state: SystemExpertState) -> Literal["clarify", "retrieve"]:
        return "clarify" if state.get("clarification_needed", False) else "retrieve"

    async def _analyze_intent_node(state: SystemExpertState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        if not messages:
            return {"error": "No messages found in state"}

        user_input = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
        context = "\n".join([f"{type(m).__name__}: {m.content}" for m in messages[-6:-1]])
        prompt = INTENT_ANALYSIS_PROMPT.format(user_input=user_input, context=context)

        try:
            response = await llm.chat_with_retry(
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            analysis = json.loads(content)
            intent = analysis.get("intent", "unknown")
            entities = analysis.get("entities", {})
            confidence = float(analysis.get("confidence", 0.0))
            clarification_needed = analysis.get("clarification_needed", False)
            clarification_reason = analysis.get("clarification_reason", "")

            if confidence < confidence_threshold:
                clarification_needed = True
                if not clarification_reason:
                    clarification_reason = "用户意图不明确，请要求提供更多细节。"

            return {
                "intent": intent,
                "entities": entities,
                "confidence": confidence,
                "clarification_needed": clarification_needed,
                "error": clarification_reason if clarification_needed else None,
            }
        except Exception as e:
            logger.error("Intent analysis failed: %s", e)
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "clarification_needed": True,
                "error": f"Analysis error: {str(e)}",
            }

    async def _clarify_node(state: SystemExpertState) -> Dict[str, Any]:
        reason = state.get("error", "需要更多信息")
        prompt = CLARIFICATION_PROMPT.format(clarification_reason=reason)
        try:
            response = await llm.chat_with_retry(messages=[{"role": "system", "content": prompt}])
            clarify_msg = AIMessage(content=response.content)
            return {
                "result": {"status": "clarification_requested", "answer": response.content},
                "messages": [clarify_msg],
            }
        except Exception as e:
            logger.error("Clarification generation failed: %s", e)
            fallback = "抱歉，我暂时无法理解您的问题，能请您换个说法吗？"
            return {
                "result": {"status": "error", "answer": fallback},
                "messages": [AIMessage(content=fallback)],
            }

    async def _retrieve_knowledge_node(state: SystemExpertState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        user_input = messages[-1].content if messages else ""
        entities = state.get("entities", {})
        results = kb_tool.search(query=user_input, entities=entities)
        return {"knowledge_results": results}

    async def _generate_response_node(state: SystemExpertState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        user_input = messages[-1].content if messages else ""
        kb_results = state.get("knowledge_results", [])
        kb_text = json.dumps(kb_results, ensure_ascii=False, indent=2) if kb_results else "未检索到相关知识。"

        prompt = GENERATE_RESPONSE_PROMPT.format(user_input=user_input, knowledge_results=kb_text)
        try:
            response = await llm.chat_with_retry(messages=[{"role": "system", "content": prompt}])
            answer_msg = AIMessage(content=response.content)
            return {
                "result": {
                    "status": "success",
                    "answer": response.content,
                    "references": [r.get("id") for r in kb_results],
                },
                "messages": [answer_msg],
            }
        except Exception as e:
            logger.error("Response generation failed: %s", e)
            return {
                "result": {"status": "error", "answer": "生成回复时发生错误。"},
                "messages": [AIMessage(content="抱歉，生成回复时发生了错误。")],
            }

    workflow = StateGraph(SystemExpertState)
    workflow.add_node("analyze_intent", _analyze_intent_node)
    workflow.add_node("clarify", _clarify_node)
    workflow.add_node("retrieve_knowledge", _retrieve_knowledge_node)
    workflow.add_node("generate_response", _generate_response_node)

    workflow.set_entry_point("analyze_intent")
    workflow.add_conditional_edges(
        "analyze_intent",
        _route_after_analysis,
        {"clarify": "clarify", "retrieve": "retrieve_knowledge"},
    )
    workflow.add_edge("retrieve_knowledge", "generate_response")
    workflow.add_edge("generate_response", END)
    workflow.add_edge("clarify", END)

    return workflow.compile()


class SystemExpertAgent(Agent):
    """
    智能对话 Agent 系统，用于处理特定系统相关的专业问题。
    具备意图识别、上下文记忆、知识库检索和主动澄清功能。
    """

    def __init__(self, name: str = "system_expert_agent"):
        super().__init__(
            name=name,
            description="Intelligent conversational agent for system expertise, FAQs, and troubleshooting.",
            config={"confidence_threshold": 0.7},
        )
        self.kb_tool = KnowledgeBaseTool()
        self.llm = LLMService()
        self.workflow = build_system_expert_graph(
            kb_tool=self.kb_tool,
            llm=self.llm,
            confidence_threshold=self.config.get("confidence_threshold", 0.7),
        )

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构: {"query": "用户问题"}
        """
        initial_state = {
            "messages": [HumanMessage(content=task.get("query", ""))],
            "task": task,
        }
        final_state = await self.workflow.ainvoke(initial_state)
        return final_state.get("result", {})
