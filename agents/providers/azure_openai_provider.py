"""
Azure OpenAI 提供商实现，使用 2024-10-21 API 版本。
"""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urljoin

import httpx
import json_repair

from providers.base import LLMProvider, LLMResponse, ToolCallRequest

# 允许发送给 Azure OpenAI 的消息键名集合
_AZURE_MSG_KEYS = frozenset({"role", "content", "tool_calls", "tool_call_id", "name"})


class AzureOpenAIProvider(LLMProvider):
    """
    符合 2024-10-21 API 版本的 Azure OpenAI 提供商。

    特点：
    - 硬编码使用 API 版本 2024-10-21
    - 在 URL 路径中使用 model 字段作为 Azure 部署名称 (deployment name)
    - 使用 api-key 请求头代替 Authorization Bearer
    - 使用 max_completion_tokens 代替 max_tokens
    - 直接进行 HTTP 调用，绕过 LiteLLM
    """

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "",
        default_model: str = "gpt-5.2-chat",
    ):
        """
        初始化 Azure OpenAI 提供商。
        
        :param api_key: Azure OpenAI API 密钥
        :param api_base: Azure OpenAI 端点 URL
        :param default_model: 默认模型（即默认部署名称）
        """
        super().__init__(api_key, api_base)
        self.default_model = default_model
        # 固定的 API 版本
        self.api_version = "2024-10-21"

        # 验证必填参数
        if not api_key:
            raise ValueError("Azure OpenAI api_key is required")  # 必须提供 api_key
        if not api_base:
            raise ValueError("Azure OpenAI api_base is required")  # 必须提供 api_base

        # 确保 api_base 以斜杠 / 结尾
        if not api_base.endswith('/'):
            api_base += '/'
        self.api_base = api_base

    def _build_chat_url(self, deployment_name: str) -> str:
        """
        构建 Azure OpenAI 的聊天补全 (chat completions) URL。
        
        :param deployment_name: 部署名称
        :return: 完整的 API 请求 URL
        """
        # Azure OpenAI URL 格式：
        # https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version={version}
        base_url = self.api_base
        if not base_url.endswith('/'):
            base_url += '/'

        # 拼接路径
        url = urljoin(
            base_url,
            f"openai/deployments/{deployment_name}/chat/completions"
        )
        # 添加 API 版本查询参数
        return f"{url}?api-version={self.api_version}"

    def _build_headers(self) -> dict[str, str]:
        """
        构建带有 api-key 的 Azure OpenAI API 请求头。
        
        :return: 包含请求头的字典
        """
        return {
            "Content-Type": "application/json",
            "api-key": self.api_key,  # Azure OpenAI 使用 api-key 请求头，而不是 Authorization
            "x-session-affinity": uuid.uuid4().hex,  # 用于后端缓存局部性
        }

    @staticmethod
    def _supports_temperature(
        deployment_name: str,
        reasoning_effort: str | None = None,
    ) -> bool:
        """
        判断当前部署模型是否可能支持 temperature 参数。
        
        :param deployment_name: 部署名称
        :param reasoning_effort: 推理力度参数
        :return: 如果支持温度参数则返回 True，否则返回 False
        """
        # 如果启用了推理力度，通常不支持 temperature
        if reasoning_effort:
            return False
        name = deployment_name.lower()
        # 排除包含 gpt-5, o1, o3, o4 的模型，因为这些较新的或带有内置推理的模型可能不支持显式的温度设置
        return not any(token in name for token in ("gpt-5", "o1", "o3", "o4"))

    def _prepare_request_payload(
        self,
        deployment_name: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        准备符合 Azure OpenAI 2024-10-21 规范的请求载荷。
        
        :param deployment_name: 部署名称
        :param messages: 消息列表
        :param tools: 工具列表
        :param max_tokens: 最大生成 Token 数
        :param temperature: 采样温度
        :param reasoning_effort: 推理力度
        :param tool_choice: 工具选择策略
        :return: 序列化为 JSON 的请求载荷字典
        """
        payload: dict[str, Any] = {
            # 清理消息中的空内容并过滤非标准键
            "messages": self._sanitize_request_messages(
                self._sanitize_empty_content(messages),
                _AZURE_MSG_KEYS,
            ),
            # Azure API 2024-10-21 使用 max_completion_tokens
            "max_completion_tokens": max(1, max_tokens),
        }

        # 如果模型支持，则添加 temperature 参数
        if self._supports_temperature(deployment_name, reasoning_effort):
            payload["temperature"] = temperature

        # 添加推理力度参数
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        # 附加工具配置
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"

        return payload

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
        向 Azure OpenAI 发送聊天补全请求。

        :param messages: 包含 'role' 和 'content' 的消息字典列表
        :param tools: 可选的 OpenAI 格式工具定义列表
        :param model: 模型标识符（用作部署名称）
        :param max_tokens: 响应中的最大 Token 数（将映射为 max_completion_tokens）
        :param temperature: 采样温度
        :param reasoning_effort: 可选的推理力度参数
        :param tool_choice: 工具选择策略
        :return: 包含文本内容和/或工具调用的 LLMResponse 对象
        """
        # 获取要使用的部署名称
        deployment_name = model or self.default_model
        
        # 准备 URL、请求头和请求载荷
        url = self._build_chat_url(deployment_name)
        headers = self._build_headers()
        payload = self._prepare_request_payload(
            deployment_name, messages, tools, max_tokens, temperature, reasoning_effort,
            tool_choice=tool_choice,
        )

        try:
            # 发起异步 HTTP POST 请求
            async with httpx.AsyncClient(timeout=60.0, verify=True) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                # 检查响应状态码是否正常
                if response.status_code != 200:
                    return LLMResponse(
                        content=f"Azure OpenAI API Error {response.status_code}: {response.text}",
                        finish_reason="error",
                    )

                response_data = response.json()
                return self._parse_response(response_data)

        except Exception as e:
            # 捕获网络或请求过程中的其他异常
            return LLMResponse(
                content=f"Error calling Azure OpenAI: {repr(e)}",
                finish_reason="error",
            )

    def _parse_response(self, response: dict[str, Any]) -> LLMResponse:
        """
        将 Azure OpenAI 的响应解析为标准的 LLMResponse 格式。
        
        :param response: 原始响应字典
        :return: 解析后的 LLMResponse 对象
        """
        try:
            choice = response["choices"][0]
            message = choice["message"]

            # ========== 解析工具调用 ==========
            tool_calls = []
            if message.get("tool_calls"):
                for tc in message["tool_calls"]:
                    # 如果参数是 JSON 字符串，则使用 json_repair 解析为字典
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        args = json_repair.loads(args)

                    tool_calls.append(
                        ToolCallRequest(
                            id=tc["id"],
                            name=tc["function"]["name"],
                            arguments=args,
                        )
                    )

            # ========== 解析 Token 消耗统计 ==========
            usage = {}
            if response.get("usage"):
                usage_data = response["usage"]
                usage = {
                    "prompt_tokens": usage_data.get("prompt_tokens", 0),
                    "completion_tokens": usage_data.get("completion_tokens", 0),
                    "total_tokens": usage_data.get("total_tokens", 0),
                }

            # 提取推理过程内容（如果模型支持）
            reasoning_content = message.get("reasoning_content") or None

            # 构建并返回最终的响应对象
            return LLMResponse(
                content=message.get("content"),
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason", "stop"),
                usage=usage,
                reasoning_content=reasoning_content,
            )

        except (KeyError, IndexError) as e:
            # 捕获解析过程中的缺失字段异常
            return LLMResponse(
                content=f"Error parsing Azure OpenAI response: {str(e)}",
                finish_reason="error",
            )

    def get_default_model(self) -> str:
        """
        获取默认模型（也被用作默认部署名称）。
        
        :return: 默认部署名称字符串
        """
        return self.default_model

