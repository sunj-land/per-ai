from dataclasses import dataclass, field
import os
import logging
import json
from typing import List, Dict, Any, Generator, Optional, AsyncGenerator, Union
import litellm
from litellm import completion, acompletion

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """
    LLM 响应数据类
    封装了从 LLM 返回的各种信息
    """
    content: Optional[str] = None          # 响应内容
    tool_calls: List[Any] = field(default_factory=list) # 工具调用列表
    reasoning_content: Optional[str] = None # 推理内容（如果模型支持）
    thinking_blocks: Optional[List[Dict]] = None # 思考块（如果模型支持）
    finish_reason: Optional[str] = None    # 结束原因（如 stop, length, tool_calls 等）

    @property
    def has_tool_calls(self) -> bool:
        """检查响应是否包含工具调用。"""
        return bool(self.tool_calls)

class LLMService:
    """
    统一 LLM 服务类，使用 litellm 库。
    支持多种提供商（Ollama, OpenAI, Anthropic 等）。
    """
    def __init__(self):
        # 从环境变量中读取默认配置
        self.default_model = os.getenv("AI_MODEL", "ollama/qwen3-vl:8b")
        self.default_api_key = os.getenv("AI_API_KEY", "")
        self.default_base_url = os.getenv("AI_API_BASE", "")

        # 配置 litellm
        litellm.drop_params = True # 丢弃不支持的参数，防止报错
        litellm.set_verbose = False # 设置为 True 可用于调试

    async def chat_with_retry(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        tool_choice: Optional[Any] = None,
        max_retries: int = 3,
        **kwargs
    ) -> LLMResponse:
        """
        带有重试逻辑和工具支持的聊天补全方法。
        匹配 AgentLoop 期望的接口。

        Args:
            messages (List[Dict[str, Any]]): 消息历史列表。
            tools (Optional[List[Dict[str, Any]]], optional): 可用工具定义列表。
            model (Optional[str], optional): 使用的模型名称。
            tool_choice (Optional[Any], optional): 强制工具选择策略。
            max_retries (int, optional): 最大重试次数。默认为 3。
            **kwargs: 其他传递给 litellm 的参数。

        Returns:
            LLMResponse: 封装后的 LLM 响应对象。
        """
        # Add a timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 300.0

        messages = [msg for msg in messages if msg.get("content")]
        model = model or self.default_model
        params = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            **kwargs
        }

        # 如果 kwargs 或 defaults 中提供了 api_key/base_url，则添加到参数中
        if "api_key" not in params and self.default_api_key:
            params["api_key"] = self.default_api_key
        if "base_url" not in params and self.default_base_url:
            params["base_url"] = self.default_base_url

        # 清理 None 值参数
        params = {k: v for k, v in params.items() if v is not None}

        for attempt in range(max_retries + 1):
            try:
                # 调用 litellm 的异步补全接口
                response = await acompletion(**params)
                message = response.choices[0].message

                tool_calls = []
                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_calls = message.tool_calls

                return LLMResponse(
                    content=message.content,
                    tool_calls=tool_calls,
                    reasoning_content=getattr(message, "reasoning_content", None),
                    thinking_blocks=getattr(message, "thinking_blocks", None),
                    finish_reason=response.choices[0].finish_reason
                )
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"LLM call failed (attempt {attempt+1}/{max_retries+1}): {e}")
                    continue
                logger.error(f"LLM call failed after {max_retries+1} attempts: {e}")
                # 返回错误响应而不是抛出异常，让循环处理
                return LLMResponse(
                    content=f"Error calling LLM: {str(e)}",
                    finish_reason="error"
                )

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        json_mode: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        基础聊天补全方法。

        Args:
            messages: 消息字典列表 [{"role": "user", "content": "..."}]
            model: 模型名称 (e.g., "gpt-4", "ollama/llama3")
            temperature: 采样温度，控制随机性
            max_tokens: 最大生成 token 数
            stream: 是否流式返回
            json_mode: 是否强制 JSON 输出
            **kwargs: 其他参数

        Returns:
            Union[str, AsyncGenerator[str, None]]: 响应字符串或产生数据块的异步生成器
        """
        model = model or self.default_model

        # 准备参数
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        # 添加 API key/base_url
        if "api_key" in kwargs:
            params["api_key"] = kwargs["api_key"]
        elif self.default_api_key:
            params["api_key"] = self.default_api_key

        if "base_url" in kwargs:
            params["base_url"] = kwargs["base_url"]
        elif self.default_base_url:
            params["base_url"] = self.default_base_url

        # Add timeout if specified
        if "timeout" in kwargs:
            params["timeout"] = kwargs["timeout"]
        else:
            params["timeout"] = 60.0  # Default timeout reduced to 60s to fail fast before frontend times out

        # 处理 JSON 模式
        if json_mode:
            params["response_format"] = {"type": "json_object"}

        try:
            if stream:
                return self._stream_chat(params)
            else:
                response = await acompletion(**params)
                return response.choices[0].message.content
        except litellm.exceptions.Timeout as e:
            logger.error(f"LLM Chat timeout: {e}")
            raise TimeoutError("大模型调用超时") from e
        except Exception as e:
            logger.error(f"LLM Chat failed: {e}")
            raise

    async def _stream_chat(self, params: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        内部方法，处理流式响应。
        生成用于 SSE 的 JSON 字符串。
        """
        try:
            response = await acompletion(**params)
            async for chunk in response:
                # 提取内容和推理（思考过程）
                try:
                    # Handle both object and dict formats from litellm chunk
                    choices = chunk.choices if hasattr(chunk, 'choices') else chunk.get("choices", [])
                    if not choices:
                        continue

                    choice = choices[0]
                    delta = choice.delta if hasattr(choice, 'delta') else choice.get("delta", {})

                    if isinstance(delta, dict):
                        content = delta.get("content", "")
                        reasoning = delta.get("reasoning_content", None)
                    else:
                        content = getattr(delta, "content", "") or ""
                        reasoning = getattr(delta, "reasoning_content", None)

                    finish_reason = choice.finish_reason if hasattr(choice, 'finish_reason') else choice.get("finish_reason")

                    # 构建响应对象
                    data = {
                        "content": content,
                        "reasoning": reasoning, # 针对支持思考过程的模型
                        "finish_reason": finish_reason
                    }

                    # 作为 JSON 字符串生成
                    yield json.dumps(data) + "\n"
                except Exception as chunk_e:
                    logger.error(f"Error processing chunk: {chunk_e}")
                    yield json.dumps({"error": f"Chunk processing error: {str(chunk_e)}"}) + "\n"
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield json.dumps({"error": str(e)}) + "\n"

    def chat_sync(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        json_mode: bool = False,
        **kwargs
    ) -> Union[str, Generator[str, None, None]]:
        """
        同步聊天补全方法。
        参数与 chat 方法相同。
        """
        model = model or self.default_model

        # 准备参数
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        # 添加 API key/base_url
        if "api_key" in kwargs:
            params["api_key"] = kwargs["api_key"]
        elif self.default_api_key:
            params["api_key"] = self.default_api_key

        if "base_url" in kwargs:
            params["base_url"] = kwargs["base_url"]
        elif self.default_base_url:
            params["base_url"] = self.default_base_url

        # 处理 JSON 模式
        if json_mode:
            params["response_format"] = {"type": "json_object"}

        try:
            if stream:
                response = completion(**params)
                for chunk in response:
                    delta = chunk.choices[0].delta
                    content = delta.content or ""
                    reasoning = getattr(delta, "reasoning_content", None)
                    data = {
                        "content": content,
                        "reasoning": reasoning,
                        "finish_reason": chunk.choices[0].finish_reason
                    }
                    yield json.dumps(data) + "\n"
            else:
                response = completion(**params)
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Chat Sync failed: {e}")
            raise

llm_service = LLMService()
