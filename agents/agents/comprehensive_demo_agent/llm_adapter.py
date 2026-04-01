import json
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage, ToolCall
from providers.litellm_provider import LiteLLMProvider
from providers.base import ToolCallRequest

def convert_to_dicts(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """将 LangChain 消息转换为 LiteLLM 支持的字典格式。"""
    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            msg_dict = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"])
                        }
                    } for tc in msg.tool_calls
                ]
            result.append(msg_dict)
        elif isinstance(msg, SystemMessage):
            result.append({"role": "system", "content": msg.content})
        elif isinstance(msg, ToolMessage):
            result.append({
                "role": "tool",
                "content": msg.content,
                "tool_call_id": msg.tool_call_id
            })
    return result

def convert_to_ai_message(response) -> AIMessage:
    """将 LLMResponse 转换为 LangChain 的 AIMessage。"""
    tool_calls = []
    for tc in response.tool_calls:
        # 假设 tc 是 ToolCallRequest
        tool_calls.append(ToolCall(
            id=tc.id,
            name=tc.name,
            args=tc.arguments if isinstance(tc.arguments, dict) else json.loads(tc.arguments)
        ))
    return AIMessage(content=response.content or "", tool_calls=tool_calls)
