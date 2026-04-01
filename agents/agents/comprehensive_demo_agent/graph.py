import json
import logging
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage

from core.agent import Agent
from providers.litellm_provider import LiteLLMProvider
from .state import DemoAgentState
from .tools import TOOLS
from .llm_adapter import convert_to_dicts, convert_to_ai_message

logger = logging.getLogger(__name__)


def build_comprehensive_demo_graph(
    llm_provider: LiteLLMProvider,
    tools_schema: list,
    tools_map: dict,
):
    """
    构建完整的 ReAct 循环演示工作流（独立函数，可单独测试或复用）。
    演示：State/Memory、工具调用、中断机制、错误处理。

    :param llm_provider: LiteLLMProvider 实例
    :param tools_schema: 传递给模型的工具 schema 列表
    :param tools_map: 工具名称 → 工具实例的字典
    :return: 编译后的 CompiledStateGraph（带 interrupt_before=["human_review"]）
    """

    async def _call_model(state: DemoAgentState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        long_term = state.get("long_term_memory", {})

        sys_prompt = "你是一个综合性的智能助手。你可以使用工具（如搜索、计算、文件操作）。\n"
        if long_term:
            sys_prompt += f"用户的长期记忆/偏好: {json.dumps(long_term, ensure_ascii=False)}\n"

        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=sys_prompt)] + list(messages)

        dict_messages = convert_to_dicts(messages)

        try:
            response = await llm_provider.chat_with_retry(
                messages=dict_messages,
                tools=tools_schema,
                temperature=0.7,
            )
            if response.finish_reason == "error":
                return {"error": response.content}

            ai_message = convert_to_ai_message(response)

            requires_input = any(
                tc["name"] == "file_operation" and tc["args"].get("action") == "write"
                for tc in ai_message.tool_calls
            )

            return {"messages": [ai_message], "requires_user_input": requires_input, "error": None}

        except Exception as e:
            logger.error("LLM call failed: %s", e)
            error_msg = AIMessage(content="抱歉，处理您的请求时模型调用失败。")
            return {"messages": [error_msg], "error": str(e)}

    async def _call_tools(state: DemoAgentState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        last_message = messages[-1]
        tool_results = {}
        tool_messages = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            if tool_name in tools_map:
                try:
                    result = await tools_map[tool_name].ainvoke(tool_args)
                    tool_results[tool_name] = result
                    tool_messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_call["id"], name=tool_name)
                    )
                except Exception as e:
                    tool_messages.append(
                        ToolMessage(
                            content=f"工具 {tool_name} 执行失败: {str(e)}",
                            tool_call_id=tool_call["id"],
                            name=tool_name,
                        )
                    )
            else:
                tool_messages.append(
                    ToolMessage(
                        content=f"未知工具: {tool_name}",
                        tool_call_id=tool_call["id"],
                        name=tool_name,
                    )
                )

        return {"messages": tool_messages, "tool_results": tool_results}

    async def _human_review(state: DemoAgentState) -> Dict[str, Any]:
        return {"requires_user_input": False}

    def _route_agent_output(state: DemoAgentState) -> Literal["action", "human_review", "end"]:
        if state.get("error"):
            return "end"
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        if not isinstance(last_message, AIMessage):
            return "end"
        if last_message.tool_calls:
            return "human_review" if state.get("requires_user_input") else "action"
        return "end"

    workflow = StateGraph(DemoAgentState)
    workflow.add_node("agent", _call_model)
    workflow.add_node("action", _call_tools)
    workflow.add_node("human_review", _human_review)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        _route_agent_output,
        {"action": "action", "human_review": "human_review", "end": END},
    )
    workflow.add_edge("action", "agent")
    workflow.add_edge("human_review", "action")

    return workflow.compile(interrupt_before=["human_review"])


class ComprehensiveDemoAgent(Agent):
    """
    完整的 LangGraph Agent 示例。
    演示：State/Memory、工具调用、中断机制、LiteLLMProvider、错误处理。
    """

    def __init__(self, name: str = "comprehensive_demo_agent"):
        import os

        super().__init__(
            name=name,
            description="A comprehensive LangGraph demo agent with tools, memory, and interrupts.",
            config={},
        )

        api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        self.llm_provider = LiteLLMProvider(default_model="dashscope/deepseek-r1", api_key=api_key)

        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": (
                        tool.args_schema.model_json_schema()
                        if tool.args_schema
                        else {"type": "object", "properties": {}}
                    ),
                },
            }
            for tool in TOOLS
        ]
        self.tools_map = {tool.name: tool for tool in TOOLS}

        self.workflow = build_comprehensive_demo_graph(
            llm_provider=self.llm_provider,
            tools_schema=self.tools_schema,
            tools_map=self.tools_map,
        )

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构:
        {
            "thread_id": "optional_thread",
            "input": "用户输入",
            "memory": {}
        }
        """
        thread_id = task.get("thread_id", "default_thread")
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "messages": [("user", task.get("input", task.get("query", "")))],
            "long_term_memory": task.get("memory", {}),
        }
        final_state = await self.workflow.ainvoke(initial_state, config=config)
        messages = final_state.get("messages", [])
        answer = messages[-1].content if messages else ""
        return {"status": "success", "answer": answer}
