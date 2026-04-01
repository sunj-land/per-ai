"""
基础大语言模型(LLM)提供商接口定义模块。
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class ToolCallRequest:
    """
    大语言模型发出的工具调用请求。
    """
    # 工具调用的唯一标识符
    id: str
    # 要调用的工具名称
    name: str
    # 传递给工具的参数字典
    arguments: dict[str, Any]
    # 提供商特定的额外字段（可选）
    provider_specific_fields: dict[str, Any] | None = None
    # 函数级别提供商特定的额外字段（可选）
    function_provider_specific_fields: dict[str, Any] | None = None

    def to_openai_tool_call(self) -> dict[str, Any]:
        """
        序列化为 OpenAI 风格的 tool_call 载荷字典。
        
        :return: 包含工具调用信息的字典
        """
        # 构建基础的 OpenAI 工具调用格式
        tool_call = {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments, ensure_ascii=False),
            },
        }
        # 如果存在提供商特定的字段，则附加到结果中
        if self.provider_specific_fields:
            tool_call["provider_specific_fields"] = self.provider_specific_fields
        # 如果存在函数级别提供商特定的字段，则附加到结果中
        if self.function_provider_specific_fields:
            tool_call["function"]["provider_specific_fields"] = self.function_provider_specific_fields
        return tool_call


@dataclass
class LLMResponse:
    """
    大语言模型提供商返回的响应结果。
    """
    # 模型生成的文本内容，如果无内容则为 None
    content: str | None
    # 模型生成的工具调用列表
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    # 生成结束的原因，默认为 "stop"
    finish_reason: str = "stop"
    # Token 消耗统计信息
    usage: dict[str, int] = field(default_factory=dict)
    # 推理过程内容（如 Kimi, DeepSeek-R1 等支持）
    reasoning_content: str | None = None
    # Anthropic 扩展的思考过程块
    thinking_blocks: list[dict] | None = None
    
    @property
    def has_tool_calls(self) -> bool:
        """
        检查响应中是否包含工具调用。
        
        :return: 布尔值，如果存在工具调用返回 True
        """
        return len(self.tool_calls) > 0


@dataclass(frozen=True)
class GenerationSettings:
    """
    LLM 调用的默认生成参数设置。

    存储在提供商实例上，使得所有调用点都能继承相同的默认值，
    而无需在每一层传递 temperature / max_tokens / reasoning_effort 参数。
    单独的调用点仍然可以通过向 chat() / chat_with_retry() 传递明确的关键字参数进行覆盖。
    """
    # 采样温度，控制输出的随机性
    temperature: float = 0.7
    # 响应的最大 Token 数
    max_tokens: int = 4096
    # 推理力度（如支持该参数的模型使用）
    reasoning_effort: str | None = None


class LLMProvider(ABC):
    """
    大语言模型提供商的抽象基类。
    
    实现类应当处理各个提供商 API 的具体细节，同时保持一致的接口。
    """

    # 聊天重试的延迟时间序列（秒）
    _CHAT_RETRY_DELAYS = (1, 2, 4)
    # 瞬时错误的匹配标记列表
    _TRANSIENT_ERROR_MARKERS = (
        "429",
        "rate limit",
        "500",
        "502",
        "503",
        "504",
        "overloaded",
        "timeout",
        "timed out",
        "connection",
        "server error",
        "temporarily unavailable",
    )
    # 不支持图片输入的错误匹配标记列表
    _IMAGE_UNSUPPORTED_MARKERS = (
        "image_url is only supported",
        "does not support image",
        "images are not supported",
        "image input is not supported",
        "image_url is not supported",
        "unsupported image input",
    )

    # 用于参数缺失检测的占位符对象
    _SENTINEL = object()

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        """
        初始化 LLMProvider。
        
        :param api_key: 访问 API 的密钥
        :param api_base: API 的基础 URL
        """
        # API 密钥
        self.api_key = api_key
        # API 基础 URL
        self.api_base = api_base
        # 默认生成设置
        self.generation: GenerationSettings = GenerationSettings()

    @staticmethod
    def _sanitize_empty_content(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        替换导致提供商返回 400 错误的空文本内容。

        当 MCP 工具未返回内容时，可能会出现空内容。大多数提供商会拒绝空字符串内容
        或者列表内容中的空文本块。
        
        :param messages: 原始消息列表
        :return: 清理后的消息列表
        """
        result: list[dict[str, Any]] = []
        for msg in messages:
            content = msg.get("content")

            # ========== 步骤1：处理内容为字符串且为空的情况 ==========
            if isinstance(content, str) and not content:
                clean = dict(msg)
                # 如果是助手角色且包含工具调用，则允许内容为 None，否则替换为 "(empty)"
                clean["content"] = None if (msg.get("role") == "assistant" and msg.get("tool_calls")) else "(empty)"
                result.append(clean)
                continue

            # ========== 步骤2：处理内容为列表的情况 ==========
            if isinstance(content, list):
                # 过滤掉空的文本块
                filtered = [
                    item for item in content
                    if not (
                        isinstance(item, dict)
                        and item.get("type") in ("text", "input_text", "output_text")
                        and not item.get("text")
                    )
                ]
                # 如果有内容被过滤掉
                if len(filtered) != len(content):
                    clean = dict(msg)
                    if filtered:
                        clean["content"] = filtered
                    elif msg.get("role") == "assistant" and msg.get("tool_calls"):
                        clean["content"] = None
                    else:
                        clean["content"] = "(empty)"
                    result.append(clean)
                    continue

            # ========== 步骤3：处理内容为字典的情况 ==========
            if isinstance(content, dict):
                clean = dict(msg)
                # 将字典包装成列表
                clean["content"] = [content]
                result.append(clean)
                continue

            # 默认情况直接追加
            result.append(msg)
        return result

    @staticmethod
    def _sanitize_request_messages(
        messages: list[dict[str, Any]],
        allowed_keys: frozenset[str],
    ) -> list[dict[str, Any]]:
        """
        仅保留提供商允许的消息键，并标准化助手内容。
        
        :param messages: 原始消息列表
        :param allowed_keys: 允许的键集合
        :return: 清理后的消息列表
        """
        sanitized = []
        for msg in messages:
            # 过滤不允许的键
            clean = {k: v for k, v in msg.items() if k in allowed_keys}
            # 如果是助手角色但缺失 content 键，则补全为 None
            if clean.get("role") == "assistant" and "content" not in clean:
                clean["content"] = None
            sanitized.append(clean)
        return sanitized

    @abstractmethod
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
        
        :param messages: 消息列表，包含 'role' 和 'content'
        :param tools: 可选的工具定义列表
        :param model: 模型标识符（提供商特定）
        :param max_tokens: 响应的最大 Token 数
        :param temperature: 采样温度
        :param reasoning_effort: 推理力度（针对支持该参数的模型）
        :param tool_choice: 工具选择策略 ("auto", "required", 或特定工具字典)
        :return: 包含内容和/或工具调用的响应对象 LLMResponse
        """
        pass

    @classmethod
    def _is_transient_error(cls, content: str | None) -> bool:
        """
        判断错误是否为瞬时错误（如限流、超时等）。
        
        :param content: 错误内容文本
        :return: 如果是瞬时错误则返回 True
        """
        err = (content or "").lower()
        return any(marker in err for marker in cls._TRANSIENT_ERROR_MARKERS)

    @classmethod
    def _is_image_unsupported_error(cls, content: str | None) -> bool:
        """
        判断错误是否因为模型不支持图片输入。
        
        :param content: 错误内容文本
        :return: 如果是不支持图片错误则返回 True
        """
        err = (content or "").lower()
        return any(marker in err for marker in cls._IMAGE_UNSUPPORTED_MARKERS)

    @staticmethod
    def _strip_image_content(messages: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        """
        将 image_url 块替换为文本占位符。如果没有找到图片则返回 None。
        
        :param messages: 消息列表
        :return: 移除图片后的消息列表，若无图片则返回 None
        """
        found = False
        result = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                new_content = []
                for b in content:
                    # 查找并替换 image_url 类型的内容
                    if isinstance(b, dict) and b.get("type") == "image_url":
                        new_content.append({"type": "text", "text": "[image omitted]"})
                        found = True
                    else:
                        new_content.append(b)
                result.append({**msg, "content": new_content})
            else:
                result.append(msg)
        return result if found else None

    async def _safe_chat(self, **kwargs: Any) -> LLMResponse:
        """
        调用 chat() 并将未预料到的异常转换为错误响应。
        
        :param kwargs: 传递给 chat 的参数
        :return: LLMResponse 对象
        """
        try:
            return await self.chat(**kwargs)
        except asyncio.CancelledError:
            # 传递取消异常
            raise
        except Exception as exc:
            # 捕获异常并封装为错误响应
            return LLMResponse(content=f"Error calling LLM: {exc}", finish_reason="error")

    async def chat_with_retry(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: object = _SENTINEL,
        temperature: object = _SENTINEL,
        reasoning_effort: object = _SENTINEL,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        带有瞬时提供商故障重试机制的 chat() 调用。

        如果没有显式传递参数，则默认使用 ``self.generation`` 的参数，
        这样调用者就不需要将 temperature / max_tokens / reasoning_effort 传递到每一层。
        
        :param messages: 消息列表
        :param tools: 可选工具列表
        :param model: 模型标识符
        :param max_tokens: 最大 Token 数
        :param temperature: 采样温度
        :param reasoning_effort: 推理力度
        :param tool_choice: 工具选择策略
        :return: LLMResponse 对象
        """
        # ========== 步骤1：处理未传入的参数，使用默认配置 ==========
        if max_tokens is self._SENTINEL:
            max_tokens = self.generation.max_tokens
        if temperature is self._SENTINEL:
            temperature = self.generation.temperature
        if reasoning_effort is self._SENTINEL:
            reasoning_effort = self.generation.reasoning_effort

        # 构建请求参数字典
        kw: dict[str, Any] = dict(
            messages=messages, tools=tools, model=model,
            max_tokens=max_tokens, temperature=temperature,
            reasoning_effort=reasoning_effort, tool_choice=tool_choice,
        )

        # ========== 步骤2：执行带重试逻辑的调用 ==========
        for attempt, delay in enumerate(self._CHAT_RETRY_DELAYS, start=1):
            response = await self._safe_chat(**kw)

            # 如果没有发生错误，直接返回
            if response.finish_reason != "error":
                return response

            # 如果不是瞬时错误
            if not self._is_transient_error(response.content):
                # 检查是否为不支持图片的错误
                if self._is_image_unsupported_error(response.content):
                    stripped = self._strip_image_content(messages)
                    if stripped is not None:
                        logger.warning("Model does not support image input, retrying without images")
                        # 移除图片后重新尝试一次
                        return await self._safe_chat(**{**kw, "messages": stripped})
                return response

            # 记录瞬时错误并等待重试
            logger.warning(
                "LLM transient error (attempt {}/{}), retrying in {}s: {}",
                attempt, len(self._CHAT_RETRY_DELAYS), delay,
                (response.content or "")[:120].lower(),
            )
            await asyncio.sleep(delay)

        # 最后一次尝试
        return await self._safe_chat(**kw)

    @abstractmethod
    def get_default_model(self) -> str:
        """
        获取该提供商的默认模型。
        
        :return: 默认模型的字符串标识
        """
        pass
