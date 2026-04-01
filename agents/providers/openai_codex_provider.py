"""
OpenAI Codex 响应提供商模块。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, AsyncGenerator

import httpx
from loguru import logger
from oauth_cli_kit import get_token as get_codex_token

from providers.base import LLMProvider, LLMResponse, ToolCallRequest

# 默认的 Codex API URL
DEFAULT_CODEX_URL = "https://chatgpt.com/backend-api/codex/responses"
# 默认的请求发起者标识
DEFAULT_ORIGINATOR = "nanobot"


class OpenAICodexProvider(LLMProvider):
    """
    使用 Codex OAuth 调用 Responses API 的提供商类。
    """

    def __init__(self, default_model: str = "openai-codex/gpt-5.1-codex"):
        """
        初始化 OpenAI Codex 提供商。
        
        :param default_model: 默认使用的模型标识
        """
        super().__init__(api_key=None, api_base=None)
        self.default_model = default_model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        发送聊天补全请求。
        
        :param messages: 包含角色和内容的消息列表
        :param tools: 可选的工具列表
        :param model: 模型标识符
        :param max_tokens: 最大生成 Token 数
        :param temperature: 采样温度
        :param reasoning_effort: 推理力度
        :param tool_choice: 工具选择策略
        :return: 包含响应内容的 LLMResponse 对象
        """
        model = model or self.default_model
        # 转换消息格式，将系统提示词提取出来，并将其他消息转换为 Codex 所需的输入项
        system_prompt, input_items = _convert_messages(messages)

        # 异步获取 OAuth Token
        token = await asyncio.to_thread(get_codex_token)
        # 构建请求头
        headers = _build_headers(token.account_id, token.access)

        # 构建请求载荷
        body: dict[str, Any] = {
            "model": _strip_model_prefix(model),
            "store": False,
            "stream": True,
            "instructions": system_prompt,
            "input": input_items,
            "text": {"verbosity": "medium"},
            "include": ["reasoning.encrypted_content"],
            "prompt_cache_key": _prompt_cache_key(messages),
            "tool_choice": tool_choice or "auto",
            "parallel_tool_calls": True,
        }

        # 添加推理力度参数
        if reasoning_effort:
            body["reasoning"] = {"effort": reasoning_effort}

        # 转换工具格式并添加到载荷中
        if tools:
            body["tools"] = _convert_tools(tools)

        url = DEFAULT_CODEX_URL

        try:
            try:
                # 尝试使用证书验证发送请求
                content, tool_calls, finish_reason = await _request_codex(url, headers, body, verify=True)
            except Exception as e:
                # 如果是证书验证失败，则记录警告并尝试禁用验证重试
                if "CERTIFICATE_VERIFY_FAILED" not in str(e):
                    raise
                logger.warning("SSL certificate verification failed for Codex API; retrying with verify=False")
                content, tool_calls, finish_reason = await _request_codex(url, headers, body, verify=False)
            
            # 返回标准的响应对象
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
            )
        except Exception as e:
            # 捕获并返回错误信息
            return LLMResponse(
                content=f"Error calling Codex: {str(e)}",
                finish_reason="error",
            )

    def get_default_model(self) -> str:
        """
        获取默认模型标识。
        
        :return: 默认模型字符串
        """
        return self.default_model


def _strip_model_prefix(model: str) -> str:
    """
    移除模型名称中的 Codex 特定前缀。
    
    :param model: 原始模型名称
    :return: 移除前缀后的模型名称
    """
    if model.startswith("openai-codex/") or model.startswith("openai_codex/"):
        return model.split("/", 1)[1]
    return model


def _build_headers(account_id: str, token: str) -> dict[str, str]:
    """
    构建 API 请求的 HTTP 头信息。
    
    :param account_id: ChatGPT 账户 ID
    :param token: OAuth 访问令牌
    :return: 包含请求头信息的字典
    """
    return {
        "Authorization": f"Bearer {token}",
        "chatgpt-account-id": account_id,
        "OpenAI-Beta": "responses=experimental",
        "originator": DEFAULT_ORIGINATOR,
        "User-Agent": "nanobot (python)",
        "accept": "text/event-stream",
        "content-type": "application/json",
    }


async def _request_codex(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    verify: bool,
) -> tuple[str, list[ToolCallRequest], str]:
    """
    发起 Codex 请求并处理 Server-Sent Events (SSE) 流。
    
    :param url: 请求 URL
    :param headers: 请求头
    :param body: 请求载荷
    :param verify: 是否验证 SSL 证书
    :return: 包含响应文本、工具调用列表和结束原因的元组
    """
    async with httpx.AsyncClient(timeout=60.0, verify=verify) as client:
        async with client.stream("POST", url, headers=headers, json=body) as response:
            # 如果状态码不为 200，读取错误信息并抛出异常
            if response.status_code != 200:
                text = await response.aread()
                raise RuntimeError(_friendly_error(response.status_code, text.decode("utf-8", "ignore")))
            # 处理流式响应
            return await _consume_sse(response)


def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    将 OpenAI 的函数调用 schema 转换为 Codex 所需的扁平格式。
    
    :param tools: OpenAI 格式的工具列表
    :return: Codex 格式的工具列表
    """
    converted: list[dict[str, Any]] = []
    for tool in tools:
        fn = (tool.get("function") or {}) if tool.get("type") == "function" else tool
        name = fn.get("name")
        if not name:
            continue
        params = fn.get("parameters") or {}
        converted.append({
            "type": "function",
            "name": name,
            "description": fn.get("description") or "",
            "parameters": params if isinstance(params, dict) else {},
        })
    return converted


def _convert_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """
    将标准消息格式转换为 Codex 支持的系统指令和输入项列表。
    
    :param messages: 标准消息列表
    :return: 包含系统提示词字符串和输入项列表的元组
    """
    system_prompt = ""
    input_items: list[dict[str, Any]] = []

    for idx, msg in enumerate(messages):
        role = msg.get("role")
        content = msg.get("content")

        # 提取系统提示词
        if role == "system":
            system_prompt = content if isinstance(content, str) else ""
            continue

        # 转换用户消息
        if role == "user":
            input_items.append(_convert_user_message(content))
            continue

        # 转换助手消息
        if role == "assistant":
            # 处理文本内容
            if isinstance(content, str) and content:
                input_items.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": content}],
                        "status": "completed",
                        "id": f"msg_{idx}",
                    }
                )
            # 处理工具调用
            for tool_call in msg.get("tool_calls", []) or []:
                fn = tool_call.get("function") or {}
                call_id, item_id = _split_tool_call_id(tool_call.get("id"))
                call_id = call_id or f"call_{idx}"
                item_id = item_id or f"fc_{idx}"
                input_items.append(
                    {
                        "type": "function_call",
                        "id": item_id,
                        "call_id": call_id,
                        "name": fn.get("name"),
                        "arguments": fn.get("arguments") or "{}",
                    }
                )
            continue

        # 转换工具返回结果消息
        if role == "tool":
            call_id, _ = _split_tool_call_id(msg.get("tool_call_id"))
            output_text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": output_text,
                }
            )
            continue

    return system_prompt, input_items


def _convert_user_message(content: Any) -> dict[str, Any]:
    """
    转换用户消息内容为 Codex 输入项格式。
    
    :param content: 原始消息内容
    :return: 格式化后的用户输入项字典
    """
    if isinstance(content, str):
        return {"role": "user", "content": [{"type": "input_text", "text": content}]}
    if isinstance(content, list):
        converted: list[dict[str, Any]] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                converted.append({"type": "input_text", "text": item.get("text", "")})
            elif item.get("type") == "image_url":
                url = (item.get("image_url") or {}).get("url")
                if url:
                    converted.append({"type": "input_image", "image_url": url, "detail": "auto"})
        if converted:
            return {"role": "user", "content": converted}
    return {"role": "user", "content": [{"type": "input_text", "text": ""}]}


def _split_tool_call_id(tool_call_id: Any) -> tuple[str, str | None]:
    """
    将复合的 tool_call_id 拆分为 call_id 和 item_id。
    
    :param tool_call_id: 原始的工具调用 ID
    :return: 包含 call_id 和可选的 item_id 的元组
    """
    if isinstance(tool_call_id, str) and tool_call_id:
        if "|" in tool_call_id:
            call_id, item_id = tool_call_id.split("|", 1)
            return call_id, item_id or None
        return tool_call_id, None
    return "call_0", None


def _prompt_cache_key(messages: list[dict[str, Any]]) -> str:
    """
    生成用于缓存提示词的唯一哈希键。
    
    :param messages: 消息列表
    :return: SHA-256 哈希字符串
    """
    raw = json.dumps(messages, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _iter_sse(response: httpx.Response) -> AsyncGenerator[dict[str, Any], None]:
    """
    迭代解析 Server-Sent Events (SSE) 数据流。
    
    :param response: HTTP 流式响应对象
    :return: 异步生成器，产生解析后的 JSON 数据字典
    """
    buffer: list[str] = []
    async for line in response.aiter_lines():
        if line == "":
            if buffer:
                # 提取并合并以 "data:" 开头的行
                data_lines = [l[5:].strip() for l in buffer if l.startswith("data:")]
                buffer = []
                if not data_lines:
                    continue
                data = "\n".join(data_lines).strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    yield json.loads(data)
                except Exception:
                    continue
            continue
        buffer.append(line)


async def _consume_sse(response: httpx.Response) -> tuple[str, list[ToolCallRequest], str]:
    """
    消费并处理 SSE 数据流，聚合最终的响应结果。
    
    :param response: HTTP 流式响应对象
    :return: 包含文本内容、工具调用列表和结束原因的元组
    """
    content = ""
    tool_calls: list[ToolCallRequest] = []
    tool_call_buffers: dict[str, dict[str, Any]] = {}
    finish_reason = "stop"

    async for event in _iter_sse(response):
        event_type = event.get("type")
        
        # 处理添加新输出项事件（如工具调用初始化）
        if event_type == "response.output_item.added":
            item = event.get("item") or {}
            if item.get("type") == "function_call":
                call_id = item.get("call_id")
                if not call_id:
                    continue
                tool_call_buffers[call_id] = {
                    "id": item.get("id") or "fc_0",
                    "name": item.get("name"),
                    "arguments": item.get("arguments") or "",
                }
                
        # 处理文本增量输出事件
        elif event_type == "response.output_text.delta":
            content += event.get("delta") or ""
            
        # 处理工具参数增量输出事件
        elif event_type == "response.function_call_arguments.delta":
            call_id = event.get("call_id")
            if call_id and call_id in tool_call_buffers:
                tool_call_buffers[call_id]["arguments"] += event.get("delta") or ""
                
        # 处理工具参数输出完成事件
        elif event_type == "response.function_call_arguments.done":
            call_id = event.get("call_id")
            if call_id and call_id in tool_call_buffers:
                tool_call_buffers[call_id]["arguments"] = event.get("arguments") or ""
                
        # 处理输出项完成事件（解析并生成工具调用对象）
        elif event_type == "response.output_item.done":
            item = event.get("item") or {}
            if item.get("type") == "function_call":
                call_id = item.get("call_id")
                if not call_id:
                    continue
                buf = tool_call_buffers.get(call_id) or {}
                args_raw = buf.get("arguments") or item.get("arguments") or "{}"
                try:
                    args = json.loads(args_raw)
                except Exception:
                    args = {"raw": args_raw}
                tool_calls.append(
                    ToolCallRequest(
                        id=f"{call_id}|{buf.get('id') or item.get('id') or 'fc_0'}",
                        name=buf.get("name") or item.get("name"),
                        arguments=args,
                    )
                )
                
        # 处理响应完成事件
        elif event_type == "response.completed":
            status = (event.get("response") or {}).get("status")
            finish_reason = _map_finish_reason(status)
            
        # 处理异常事件
        elif event_type in {"error", "response.failed"}:
            raise RuntimeError("Codex response failed")

    return content, tool_calls, finish_reason


# 结束原因的映射字典
_FINISH_REASON_MAP = {"completed": "stop", "incomplete": "length", "failed": "error", "cancelled": "error"}


def _map_finish_reason(status: str | None) -> str:
    """
    将 Codex 的状态映射为标准的结束原因。
    
    :param status: Codex 状态字符串
    :return: 标准的 finish_reason
    """
    return _FINISH_REASON_MAP.get(status or "completed", "stop")


def _friendly_error(status_code: int, raw: str) -> str:
    """
    生成用户友好的错误信息。
    
    :param status_code: HTTP 状态码
    :param raw: 原始错误信息
    :return: 友好的错误描述字符串
    """
    if status_code == 429:
        return "ChatGPT usage quota exceeded or rate limit triggered. Please try again later."
    return f"HTTP {status_code}: {raw}"
