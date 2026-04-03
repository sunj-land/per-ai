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

def _prepare_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    在发送给 LLM 之前清理消息列表：
    1. 删除无用消息（无内容、无工具调用且非工具结果）。
    2. 从 assistant 消息中剥离 reasoning_content / thinking_blocks，
       这些字段仅用于当前轮次的响应，发回历史时可能导致部分提供商
       （尤其是 DeepSeek）在消息结构变换中丢失 tool_calls，
       进而触发 "tool must follow tool_calls" 错误。
    3. 校验工具消息顺序，丢弃孤立的 tool 消息（无对应 tool_calls 前驱），
       防止因边缘情况产生非法请求。
    """
    # Step 1: 过滤空消息
    filtered = [
        msg for msg in messages
        if msg.get("content") or msg.get("tool_calls") or msg.get("role") == "tool"
    ]

    # Step 2: 剥离 assistant 消息中的推理字段
    cleaned: List[Dict[str, Any]] = []
    for msg in filtered:
        if msg.get("role") == "assistant" and (
            "reasoning_content" in msg or "thinking_blocks" in msg
        ):
            msg = {k: v for k, v in msg.items() if k not in ("reasoning_content", "thinking_blocks")}
        cleaned.append(msg)

    # Step 3: 丢弃孤立的 tool 消息
    validated: List[Dict[str, Any]] = []
    for msg in cleaned:
        if msg.get("role") == "tool":
            # 检查 validated 中最后一条 assistant 消息是否带有 tool_calls
            has_tool_calls = False
            for prev in reversed(validated):
                if prev.get("role") == "assistant":
                    has_tool_calls = bool(prev.get("tool_calls"))
                    break
                elif prev.get("role") == "tool":
                    continue  # 连续的 tool 结果，继续向前找
                else:
                    break
            if not has_tool_calls:
                logger.warning(
                    "Dropping orphaned tool message (tool_call_id=%s) — no preceding assistant tool_calls found",
                    msg.get("tool_call_id"),
                )
                continue
        validated.append(msg)

    return validated


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

        messages = _prepare_messages(messages)
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

    async def chat_with_retry_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        tool_choice: Optional[Any] = None,
        max_retries: int = 3,
        **kwargs,
    ) -> AsyncGenerator[tuple, None]:
        """
        Streaming variant of chat_with_retry.

        Yields:
          ("reasoning", str)       — reasoning/thinking chunk as it arrives
          ("done", LLMResponse)    — final assembled response (always last)
        """
        if "timeout" not in kwargs:
            kwargs["timeout"] = 300.0

        messages = _prepare_messages(messages)
        model = model or self.default_model
        params = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "stream": True,
            **kwargs,
        }
        if "api_key" not in params and self.default_api_key:
            params["api_key"] = self.default_api_key
        if "base_url" not in params and self.default_base_url:
            params["base_url"] = self.default_base_url
        params = {k: v for k, v in params.items() if v is not None}

        for attempt in range(max_retries + 1):
            try:
                response = await acompletion(**params)
                full_content = ""
                full_reasoning = ""
                tool_calls_acc: Dict[int, Dict[str, Any]] = {}
                finish_reason: Optional[str] = None

                async for chunk in response:
                    choices = getattr(chunk, "choices", None) or []
                    if not choices:
                        continue
                    choice = choices[0]
                    finish_reason = getattr(choice, "finish_reason", None) or finish_reason
                    delta = getattr(choice, "delta", {})

                    if isinstance(delta, dict):
                        content_chunk = delta.get("content") or ""
                        reasoning_chunk = delta.get("reasoning_content") or ""
                        tc_deltas = delta.get("tool_calls") or []
                    else:
                        content_chunk = getattr(delta, "content", "") or ""
                        reasoning_chunk = getattr(delta, "reasoning_content", None) or ""
                        tc_deltas = getattr(delta, "tool_calls", None) or []

                    if reasoning_chunk:
                        full_reasoning += reasoning_chunk
                        yield ("reasoning", reasoning_chunk)

                    if content_chunk:
                        full_content += content_chunk
                        yield ("content_delta", content_chunk)

                    for tc_delta in tc_deltas:
                        if isinstance(tc_delta, dict):
                            idx = tc_delta.get("index", 0)
                            tc_id = tc_delta.get("id")
                            tc_type = tc_delta.get("type")
                            fn = tc_delta.get("function") or {}
                            fn_name = fn.get("name") or ""
                            fn_args = fn.get("arguments") or ""
                        else:
                            idx = getattr(tc_delta, "index", 0)
                            tc_id = getattr(tc_delta, "id", None)
                            tc_type = getattr(tc_delta, "type", None)
                            fn = getattr(tc_delta, "function", None)
                            fn_name = (getattr(fn, "name", "") or "") if fn else ""
                            fn_args = (getattr(fn, "arguments", "") or "") if fn else ""

                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc_id:
                            tool_calls_acc[idx]["id"] = tc_id
                        if tc_type:
                            tool_calls_acc[idx]["type"] = tc_type
                        if fn_name:
                            tool_calls_acc[idx]["function"]["name"] += fn_name
                        if fn_args:
                            tool_calls_acc[idx]["function"]["arguments"] += fn_args

                assembled_tool_calls = [
                    tool_calls_acc[i] for i in sorted(tool_calls_acc.keys())
                ]
                if not finish_reason:
                    finish_reason = "tool_calls" if assembled_tool_calls else "stop"

                yield (
                    "done",
                    LLMResponse(
                        content=full_content or None,
                        tool_calls=assembled_tool_calls,
                        reasoning_content=full_reasoning or None,
                        thinking_blocks=None,
                        finish_reason=finish_reason,
                    ),
                )
                return

            except Exception as e:
                if attempt < max_retries:
                    logger.warning(
                        "LLM stream failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, e
                    )
                    continue
                logger.error("LLM stream failed after %d attempts: %s", max_retries + 1, e)
                yield (
                    "done",
                    LLMResponse(content=f"Error calling LLM: {str(e)}", finish_reason="error"),
                )
                return

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
