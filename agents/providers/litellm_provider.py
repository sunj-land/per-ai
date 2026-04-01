"""
支持多提供商的 LiteLLM 实现模块。
"""

import hashlib
import os
import secrets
import string
from typing import Any

import json_repair
import litellm
from litellm import acompletion
from loguru import logger

from providers.base import LLMProvider, LLMResponse, ToolCallRequest
from providers.registry import find_by_model, find_gateway

# 标准的聊天补全消息键名集合
_ALLOWED_MSG_KEYS = frozenset({"role", "content", "tool_calls", "tool_call_id", "name", "reasoning_content"})
# Anthropic 特有的消息键名集合
_ANTHROPIC_EXTRA_KEYS = frozenset({"thinking_blocks"})
# 字母数字字符集，用于生成短 ID
_ALNUM = string.ascii_letters + string.digits

def _short_tool_id() -> str:
    """
    生成一个兼容所有提供商（包括 Mistral）的 9 字符字母数字 ID。
    
    :return: 9位随机字符串
    """
    return "".join(secrets.choice(_ALNUM) for _ in range(9))


class LiteLLMProvider(LLMProvider):
    """
    使用 LiteLLM 支持多提供商的 LLM 提供商类。

    通过统一的接口支持 OpenRouter, Anthropic, OpenAI, Gemini, MiniMax 等多个提供商。
    提供商特定的逻辑由注册表驱动（见 providers/registry.py）—— 此处不需要 if-elif 链。
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_model: str = "anthropic/claude-opus-4-5",
        extra_headers: dict[str, str] | None = None,
        provider_name: str | None = None,
    ):
        """
        初始化 LiteLLMProvider。
        
        :param api_key: API 密钥
        :param api_base: API 基础 URL
        :param default_model: 默认模型标识
        :param extra_headers: 额外的 HTTP 请求头
        :param provider_name: 提供商名称（用于强制指定网关）
        """
        super().__init__(api_key, api_base)
        # 默认模型
        self.default_model = default_model
        # 额外请求头
        self.extra_headers = extra_headers or {}

        # 检测网关 / 本地部署。
        # provider_name (来自配置键) 是主要信号；
        # api_key / api_base 作为自动检测的回退。
        self._gateway = find_gateway(provider_name, api_key, api_base)

        # 配置环境变量
        if api_key:
            self._setup_env(api_key, api_base, default_model)

        if api_base:
            litellm.api_base = api_base

        # 禁用 LiteLLM 噪音日志
        litellm.suppress_debug_info = True
        # 丢弃提供商不支持的参数（例如 gpt-5 会拒绝某些参数）
        litellm.drop_params = True

        # 检查是否启用了 Langsmith
        self._langsmith_enabled = bool(os.getenv("LANGSMITH_API_KEY"))

    def _setup_env(self, api_key: str, api_base: str | None, model: str) -> None:
        """
        基于检测到的提供商设置环境变量。
        
        :param api_key: API 密钥
        :param api_base: API 基础 URL
        :param model: 模型名称
        """
        spec = self._gateway or find_by_model(model)
        if not spec:
            return
        if not spec.env_key:
            # 针对仅支持 OAuth/提供商专有的规范 (例如: openai_codex)
            return

        # 网关/本地配置覆盖现有的环境变量；标准提供商不覆盖
        if self._gateway:
            os.environ[spec.env_key] = api_key
        else:
            os.environ.setdefault(spec.env_key, api_key)

        # 解析 env_extras 占位符:
        #   {api_key}  → 用户的 API 密钥
        #   {api_base} → 用户的 api_base，回退到 spec.default_api_base
        effective_base = api_base or spec.default_api_base
        for env_name, env_val in spec.env_extras:
            resolved = env_val.replace("{api_key}", api_key)
            resolved = resolved.replace("{api_base}", effective_base)
            os.environ.setdefault(env_name, resolved)

    def _resolve_model(self, model: str) -> str:
        """
        应用提供商/网关前缀解析模型名称。
        
        :param model: 原始模型名称
        :return: 解析后的模型名称
        """
        if self._gateway:
            prefix = self._gateway.litellm_prefix
            # 如果需要剥离模型前缀
            if self._gateway.strip_model_prefix:
                model = model.split("/")[-1]
            if prefix:
                model = f"{prefix}/{model}"
            return model

        # 标准模式：为已知提供商自动添加前缀
        spec = find_by_model(model)
        if spec and spec.litellm_prefix:
            model = self._canonicalize_explicit_prefix(model, spec.name, spec.litellm_prefix)
            # 如果模型未包含跳过前缀列表中的前缀
            if not any(model.startswith(s) for s in spec.skip_prefixes):
                model = f"{spec.litellm_prefix}/{model}"

        return model

    @staticmethod
    def _canonicalize_explicit_prefix(model: str, spec_name: str, canonical_prefix: str) -> str:
        """
        规范化显式提供商前缀，例如 `github-copilot/...`。
        
        :param model: 模型名称
        :param spec_name: 规范名称
        :param canonical_prefix: 规范前缀
        :return: 规范化后的模型名称
        """
        if "/" not in model:
            return model
        prefix, remainder = model.split("/", 1)
        if prefix.lower().replace("-", "_") != spec_name:
            return model
        return f"{canonical_prefix}/{remainder}"

    def _supports_cache_control(self, model: str) -> bool:
        """
        判断提供商是否支持在内容块上使用 cache_control。
        
        :param model: 模型名称
        :return: 布尔值，支持返回 True
        """
        if self._gateway is not None:
            return self._gateway.supports_prompt_caching
        spec = find_by_model(model)
        return spec is not None and spec.supports_prompt_caching

    def _apply_cache_control(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]] | None]:
        """
        注入 cache_control 后返回消息和工具的副本。
        
        :param messages: 原始消息列表
        :param tools: 原始工具列表
        :return: 包含 cache_control 的消息和工具列表元组
        """
        new_messages = []
        # 遍历消息，为系统提示词注入缓存控制
        for msg in messages:
            if msg.get("role") == "system":
                content = msg["content"]
                if isinstance(content, str):
                    new_content = [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}]
                else:
                    new_content = list(content)
                    new_content[-1] = {**new_content[-1], "cache_control": {"type": "ephemeral"}}
                new_messages.append({**msg, "content": new_content})
            else:
                new_messages.append(msg)

        # 为最后一个工具注入缓存控制
        new_tools = tools
        if tools:
            new_tools = list(tools)
            new_tools[-1] = {**new_tools[-1], "cache_control": {"type": "ephemeral"}}

        return new_messages, new_tools

    def _apply_model_overrides(self, model: str, kwargs: dict[str, Any]) -> None:
        """
        从注册表应用模型特定的参数覆盖。
        
        :param model: 模型名称
        :param kwargs: 参数字典（将被就地修改）
        """
        model_lower = model.lower()
        spec = find_by_model(model)
        if spec:
            for pattern, overrides in spec.model_overrides:
                if pattern in model_lower:
                    kwargs.update(overrides)
                    return

    @staticmethod
    def _extra_msg_keys(original_model: str, resolved_model: str) -> frozenset[str]:
        """
        返回要在请求消息中保留的提供商特定额外键。
        
        :param original_model: 原始模型名称
        :param resolved_model: 解析后的模型名称
        :return: 额外键名的不可变集合
        """
        spec = find_by_model(original_model) or find_by_model(resolved_model)
        if (spec and spec.name == "anthropic") or "claude" in original_model.lower() or resolved_model.startswith("anthropic/"):
            return _ANTHROPIC_EXTRA_KEYS
        return frozenset()

    @staticmethod
    def _normalize_tool_call_id(tool_call_id: Any) -> Any:
        """
        将 tool_call_id 规范化为提供商安全的 9 字符字母数字格式。
        
        :param tool_call_id: 原始工具调用 ID
        :return: 规范化后的 ID
        """
        if not isinstance(tool_call_id, str):
            return tool_call_id
        if len(tool_call_id) == 9 and tool_call_id.isalnum():
            return tool_call_id
        return hashlib.sha1(tool_call_id.encode()).hexdigest()[:9]

    @staticmethod
    def _sanitize_messages(messages: list[dict[str, Any]], extra_keys: frozenset[str] = frozenset()) -> list[dict[str, Any]]:
        """
        剥离非标准键，并确保助手消息具有 content 键。
        
        :param messages: 原始消息列表
        :param extra_keys: 允许的额外键集合
        :return: 清理后的消息列表
        """
        allowed = _ALLOWED_MSG_KEYS | extra_keys
        sanitized = LLMProvider._sanitize_request_messages(messages, allowed)
        id_map: dict[str, str] = {}

        def map_id(value: Any) -> Any:
            if not isinstance(value, str):
                return value
            return id_map.setdefault(value, LiteLLMProvider._normalize_tool_call_id(value))

        for clean in sanitized:
            # 在缩短 ID 后保持助手 tool_calls[].id 和工具 tool_call_id 的同步，
            # 否则严格的提供商会拒绝断开的链接。
            if isinstance(clean.get("tool_calls"), list):
                normalized_tool_calls = []
                for tc in clean["tool_calls"]:
                    if not isinstance(tc, dict):
                        normalized_tool_calls.append(tc)
                        continue
                    tc_clean = dict(tc)
                    tc_clean["id"] = map_id(tc_clean.get("id"))
                    normalized_tool_calls.append(tc_clean)
                clean["tool_calls"] = normalized_tool_calls

            if "tool_call_id" in clean and clean["tool_call_id"]:
                clean["tool_call_id"] = map_id(clean["tool_call_id"])
        return sanitized

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
        通过 LiteLLM 发送聊天补全请求。

        :param messages: 包含 'role' 和 'content' 的消息字典列表。
        :param tools: OpenAI 格式的工具定义可选列表。
        :param model: 模型标识符（例如，'anthropic/claude-sonnet-4-5'）。
        :param max_tokens: 响应中的最大 Token 数。
        :param temperature: 采样温度。
        :param reasoning_effort: 推理力度。
        :param tool_choice: 工具选择策略。
        :return: 包含内容和/或工具调用的 LLMResponse。
        """
        # 解析模型名称
        original_model = model or self.default_model
        model = self._resolve_model(original_model)
        extra_msg_keys = self._extra_msg_keys(original_model, model)

        # 应用缓存控制（如果支持）
        if self._supports_cache_control(original_model):
            messages, tools = self._apply_cache_control(messages, tools)

        # 限制 max_tokens 至少为 1 —— 负数或零值会导致 LiteLLM 拒绝请求
        max_tokens = max(1, max_tokens)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": self._sanitize_messages(self._sanitize_empty_content(messages), extra_keys=extra_msg_keys),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # 如果是网关，注入网关的额外参数
        if self._gateway:
            kwargs.update(self._gateway.litellm_kwargs)

        # 应用模型特定的参数覆盖 (例如 kimi-k2.5 temperature)
        self._apply_model_overrides(model, kwargs)

        if self._langsmith_enabled:
            kwargs.setdefault("callbacks", []).append("langsmith")

        # 直接传递 api_key —— 比单独使用环境变量更可靠
        if self.api_key:
            kwargs["api_key"] = self.api_key

        # 为自定义端点传递 api_base
        if self.api_base:
            kwargs["api_base"] = self.api_base

        # 传递额外的请求头 (例如 AiHubMix 的 APP-Code)
        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers

        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
            kwargs["drop_params"] = True

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        try:
            # 发起异步调用
            response = await acompletion(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            # 将错误作为内容返回，以便进行优雅处理
            return LLMResponse(
                content=f"Error calling LLM: {str(e)}",
                finish_reason="error",
            )

    def _parse_response(self, response: Any) -> LLMResponse:
        """
        将 LiteLLM 响应解析为我们的标准格式。
        
        :param response: 原始 LiteLLM 响应
        :return: LLMResponse 对象
        """
        choice = response.choices[0]
        message = choice.message
        content = message.content
        finish_reason = choice.finish_reason

        # 某些提供商（例如 GitHub Copilot）将 content 和 tool_calls 拆分到多个 choice 中。
        # 合并它们，以便不丢失 tool_calls。
        raw_tool_calls = []
        for ch in response.choices:
            msg = ch.message
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                raw_tool_calls.extend(msg.tool_calls)
                if ch.finish_reason in ("tool_calls", "stop"):
                    finish_reason = ch.finish_reason
            if not content and msg.content:
                content = msg.content

        if len(response.choices) > 1:
            logger.debug("LiteLLM response has {} choices, merged {} tool_calls",
                         len(response.choices), len(raw_tool_calls))

        tool_calls = []
        # 解析合并后的工具调用
        for tc in raw_tool_calls:
            # 如果需要，从 JSON 字符串中解析参数
            args = tc.function.arguments
            if isinstance(args, str):
                args = json_repair.loads(args)

            provider_specific_fields = getattr(tc, "provider_specific_fields", None) or None
            function_provider_specific_fields = (
                getattr(tc.function, "provider_specific_fields", None) or None
            )

            tool_calls.append(ToolCallRequest(
                id=_short_tool_id(),
                name=tc.function.name,
                arguments=args,
                provider_specific_fields=provider_specific_fields,
                function_provider_specific_fields=function_provider_specific_fields,
            ))

        # 提取消耗信息
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        reasoning_content = getattr(message, "reasoning_content", None) or None
        thinking_blocks = getattr(message, "thinking_blocks", None) or None

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason or "stop",
            usage=usage,
            reasoning_content=reasoning_content,
            thinking_blocks=thinking_blocks,
        )

    def get_default_model(self) -> str:
        """
        获取默认模型。
        
        :return: 模型标识字符串
        """
        return self.default_model
