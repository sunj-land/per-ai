import asyncio
import functools
import logging
import time
import json
import re
import base64
import mimetypes
import platform
from datetime import datetime
from pathlib import Path
from typing import Callable, Type, Union, Tuple, Any, List, Dict, Optional
import tiktoken

logger = logging.getLogger(__name__)

def with_timeout(seconds: float):
    """
    装饰器：为异步函数添加超时控制。

    Args:
        seconds (float): 超时时间（秒）。

    Returns:
        Callable: 装饰后的函数。
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # 使用 asyncio.wait_for 实现超时等待
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {seconds} seconds")
                raise TimeoutError(f"Operation timed out after {seconds}s")
        return wrapper
    return decorator

def with_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = (Exception,)
):
    """
    装饰器：添加带指数退避的重试逻辑。

    Args:
        max_retries (int): 最大重试次数。
        delay (float): 初始重试延迟（秒）。
        backoff (float): 延迟倍增因子（指数退避）。
        exceptions (Union[Type[Exception], Tuple[Type[Exception], ...]]): 需要捕获并重试的异常类型。
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")

            if last_exception:
                raise last_exception
        return wrapper
    return decorator

class CircuitBreaker:
    """
    简单的断路器模式 (Circuit Breaker Pattern) 实现。
    用于防止应用程序不断地尝试执行可能会失败的操作。
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        """
        初始化断路器。

        Args:
            failure_threshold (int): 触发断路器打开的连续失败次数阈值。
            recovery_timeout (float): 断路器从打开状态进入半打开状态的恢复超时时间（秒）。
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # 状态: CLOSED (关闭/正常), OPEN (打开/熔断), HALF-OPEN (半打开/试探)

    def record_failure(self):
        """记录一次失败，并检查是否需要打开断路器。"""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("Circuit breaker OPEN")

    def record_success(self):
        """记录一次成功，重置失败计数并关闭断路器。"""
        self.failures = 0
        self.state = "CLOSED"

    def allow_request(self) -> bool:
        """
        检查是否允许执行请求。

        Returns:
            bool: 如果允许请求则返回 True，否则返回 False。
        """
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            # 如果超过恢复时间，进入半打开状态，允许一次试探性请求
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                return True
            return False
        if self.state == "HALF-OPEN":
            return True  # 允许一次试探性请求
        return True

def detect_image_mime(data: bytes) -> str | None:
    """
    通过魔术字节 (Magic Bytes) 检测图片 MIME 类型，忽略文件扩展名。

    Args:
        data (bytes): 图片文件的二进制数据。

    Returns:
        str | None: 检测到的 MIME 类型（如 'image/png'），如果无法识别则返回 None。
    """
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None

def ensure_dir(path: Path) -> Path:
    """
    确保目录存在。如果不存在则创建（包含父目录）。

    Args:
        path (Path): 目录路径。

    Returns:
        Path: 传入的目录路径。
    """
    path.mkdir(parents=True, exist_ok=True)
    return path

def timestamp() -> str:
    """返回当前的 ISO 格式时间戳字符串。"""
    return datetime.now().isoformat()

def current_time_str() -> str:
    """返回人类可读的当前时间字符串，包含星期和时区。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
    tz = time.strftime("%Z") or "UTC"
    return f"{now} ({tz})"

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*]')

def safe_filename(name: str) -> str:
    """
    将文件名中的不安全字符替换为下划线，以确保文件系统兼容性。

    Args:
        name (str): 原始文件名。

    Returns:
        str: 安全的文件名。
    """
    return _UNSAFE_CHARS.sub("_", name).strip()

def split_message(content: str, max_len: int = 2000) -> List[str]:
    """
    将长消息拆分为多个块，每个块不超过 max_len。
    优先在换行符处拆分，其次在空格处拆分，最后强制拆分。

    Args:
        content (str): 要拆分的消息内容。
        max_len (int): 每个块的最大长度。

    Returns:
        List[str]: 拆分后的消息块列表。
    """
    if not content:
        return []
    if len(content) <= max_len:
        return [content]
    chunks: List[str] = []
    while content:
        if len(content) <= max_len:
            chunks.append(content)
            break
        cut = content[:max_len]
        # 尝试优先在换行符处断开
        pos = cut.rfind('\n')
        if pos <= 0:
            # 其次尝试在空格处断开
            pos = cut.rfind(' ')
        if pos <= 0:
            # 均无法断开，强制在 max_len 处断开
            pos = max_len
        chunks.append(content[:pos])
        content = content[pos:].lstrip()
    return chunks

def build_assistant_message(
    content: Optional[str],
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    reasoning_content: Optional[str] = None,
    thinking_blocks: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    构建符合提供商要求的 Assistant 消息对象，支持可选的推理字段。

    Args:
        content (Optional[str]): 消息内容。
        tool_calls (Optional[List[Dict]]): 工具调用列表。
        reasoning_content (Optional[str]): 推理内容（Thinking Process）。
        thinking_blocks (Optional[List[Dict]]): 结构化的思考块。

    Returns:
        Dict[str, Any]: 消息字典。
    """
    msg: Dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    if reasoning_content is not None:
        msg["reasoning_content"] = reasoning_content
    if thinking_blocks:
        msg["thinking_blocks"] = thinking_blocks
    return msg

def estimate_prompt_tokens(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """
    使用 tiktoken 估算提示词 (Prompt) 的 Token 数量。
    主要针对 OpenAI 模型格式 (cl100k_base 编码)。

    Args:
        messages (List[Dict]): 消息列表。
        tools (Optional[List[Dict]]): 工具定义列表。

    Returns:
        int: 估算的 Token 总数。
    """
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        parts: List[str] = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                # 处理多模态或结构化内容
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        txt = part.get("text", "")
                        if txt:
                            parts.append(txt)
        if tools:
            parts.append(json.dumps(tools, ensure_ascii=False))
        return len(enc.encode("\n".join(parts)))
    except Exception:
        return 0

def estimate_message_tokens(message: Dict[str, Any]) -> int:
    """
    估算单条持久化消息的 Token 数量。

    Args:
        message (Dict[str, Any]): 消息对象。

    Returns:
        int: 估算的 Token 数。
    """
    content = message.get("content")
    parts: List[str] = []
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                if text:
                    parts.append(text)
            else:
                parts.append(json.dumps(part, ensure_ascii=False))
    elif content is not None:
        parts.append(json.dumps(content, ensure_ascii=False))

    # 包含其他字段
    for key in ("name", "tool_call_id"):
        value = message.get(key)
        if isinstance(value, str) and value:
            parts.append(value)
    if message.get("tool_calls"):
        parts.append(json.dumps(message["tool_calls"], ensure_ascii=False))

    payload = "\n".join(parts)
    if not payload:
        return 1
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return max(1, len(enc.encode(payload)))
    except Exception:
        # 如果 tiktoken 失败，使用字符数粗略估算 (4 chars/token)
        return max(1, len(payload) // 4)

def estimate_prompt_tokens_chain(
    provider: Any,
    model: Optional[str],
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[int, str]:
    """
    链式估算 Token 数量：
    1. 优先尝试使用 Provider 自带的 estimate_prompt_tokens 方法。
    2. 如果失败或不支持，降级使用 tiktoken 本地估算。

    Args:
        provider (Any): LLM Provider 实例。
        model (str): 模型名称。
        messages (List[Dict]): 消息列表。
        tools (List[Dict]): 工具列表。

    Returns:
        Tuple[int, str]: (Token 数量, 估算来源 'provider_counter'/'tiktoken'/'none')。
    """
    # 1. 尝试 Provider 的计数器
    provider_counter = getattr(provider, "estimate_prompt_tokens", None)
    if callable(provider_counter):
        try:
            tokens, source = provider_counter(messages, tools, model)
            if isinstance(tokens, (int, float)) and tokens > 0:
                return int(tokens), str(source or "provider_counter")
        except Exception:
            pass

    # 2. 降级到 tiktoken
    estimated = estimate_prompt_tokens(messages, tools)
    if estimated > 0:
        return int(estimated), "tiktoken"
    return 0, "none"


def strip_think(text: Optional[str]) -> Optional[str]:
    """移除模型（如 DeepSeek）在内容中嵌入的 <think>...</think> 思考块。"""
    if not text:
        return None
    return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None


def extract_think_blocks(text: Optional[str]) -> List[str]:
    """从文本中提取所有 <think>...</think> 块内的内容。"""
    if not text:
        return []
    return [
        item.strip()
        for item in re.findall(r"<think>([\s\S]*?)</think>", text)
        if isinstance(item, str) and item.strip()
    ]


def parse_json_object(raw_text: str) -> Dict[str, Any]:
    """
    宽容地解析 JSON 对象字符串。
    支持 markdown 代码块包裹，以及从文本中提取第一个 {...} 对象。
    """
    content = (raw_text or "").strip()
    if not content:
        return {}
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
