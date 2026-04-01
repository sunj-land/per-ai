"""
持久化代理记忆系统。
实现了一个双层记忆架构：
1. 长期记忆 (MEMORY.md): 存储经过总结的事实和关键信息。
2. 历史记录 (HISTORY.md): 存储完整的对话日志，支持 grep 搜索。
"""

import asyncio
import json
import weakref
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple

import logging
from utils.utils import ensure_dir, estimate_message_tokens, estimate_prompt_tokens_chain
from core.session import Session, SessionManager
from core.llm import LLMService

logger = logging.getLogger(__name__)

# 定义 save_memory 工具，用于 LLM 更新记忆
_SAVE_MEMORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save the memory consolidation result to persistent storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "history_entry": {
                        "type": "string",
                        "description": "A paragraph summarizing key events/decisions/topics. "
                        "Start with [YYYY-MM-DD HH:MM]. Include detail useful for grep search.",
                    },
                    "memory_update": {
                        "type": "string",
                        "description": "Full updated long-term memory as markdown. Include all existing "
                        "facts plus new ones. Return unchanged if nothing new.",
                    },
                },
                "required": ["history_entry", "memory_update"],
            },
        },
    }
]


def _ensure_text(value: Any) -> str:
    """
    将工具调用负载值标准化为文本以进行文件存储。

    Args:
        value (Any): 输入值。

    Returns:
        str: 字符串形式的值。
    """
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _normalize_save_memory_args(args: Any) -> Optional[Dict[str, Any]]:
    """
    将提供者的工具调用参数标准化为预期的字典形状。
    处理字符串形式的 JSON 或列表形式的参数。

    Args:
        args (Any): 原始参数。

    Returns:
        Optional[Dict[str, Any]]: 标准化后的字典，如果解析失败则为 None。
    """
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return None
    if isinstance(args, list):
        return args[0] if args and isinstance(args[0], dict) else None
    return args if isinstance(args, dict) else None

# 工具选择错误的标记，用于检测不支持 forced tool_choice 的情况
_TOOL_CHOICE_ERROR_MARKERS = (
    "tool_choice",
    "toolchoice",
    "does not support",
    'should be ["none", "auto"]',
)


def _is_tool_choice_unsupported(content: Optional[str]) -> bool:
    """
    检测是否因为强制 tool_choice 不被支持而导致的提供者错误。

    Args:
        content (Optional[str]): 错误消息内容。

    Returns:
        bool: 如果包含不支持的标记则为 True。
    """
    text = (content or "").lower()
    return any(m in text for m in _TOOL_CHOICE_ERROR_MARKERS)


class MemoryStore:
    """
    双层记忆存储管理类。
    管理 MEMORY.md (长期事实) 和 HISTORY.md (可搜索日志)。
    """

    _MAX_FAILURES_BEFORE_RAW_ARCHIVE = 3  # 降级为原始归档前的最大失败次数

    def __init__(self, workspace: Path):
        """
        初始化 MemoryStore。

        Args:
            workspace (Path): 工作区根目录。
        """
        self.memory_dir = ensure_dir(workspace / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"
        self._consecutive_failures = 0

    def read_long_term(self) -> str:
        """
        读取长期记忆内容。

        Returns:
            str: MEMORY.md 的内容，如果不存在则为空字符串。
        """
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:
        """
        写入长期记忆内容。

        Args:
            content (str): 要写入的新内容。
        """
        self.memory_file.write_text(content, encoding="utf-8")

    def append_history(self, entry: str) -> None:
        """
        追加内容到历史记录文件。

        Args:
            entry (str): 要追加的历史条目。
        """
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")

    def get_memory_context(self) -> str:
        """
        获取用于 LLM 上下文的格式化长期记忆。

        Returns:
            str: 格式化的长期记忆字符串。
        """
        long_term = self.read_long_term()
        return f"## Long-term Memory\n{long_term}" if long_term else ""

    @staticmethod
    def _format_messages(messages: List[Dict]) -> str:
        """
        将消息列表格式化为文本，用于 LLM 处理。

        Args:
            messages (List[Dict]): 消息列表。

        Returns:
            str: 格式化后的消息字符串。
        """
        lines = []
        for message in messages:
            if not message.get("content"):
                continue
            tools = f" [tools: {', '.join(message['tools_used'])}]" if message.get("tools_used") else ""
            lines.append(
                f"[{message.get('timestamp', '?')[:16]}] {message['role'].upper()}{tools}: {message['content']}"
            )
        return "\n".join(lines)

    async def consolidate(
        self,
        messages: List[Dict],
        provider: LLMService,
        model: str,
    ) -> bool:
        """
        将提供的消息块整合到 MEMORY.md 和 HISTORY.md 中。
        使用 LLM 生成摘要并更新长期记忆。

        Args:
            messages (List[Dict]): 要整合的消息列表。
            provider (LLMService): LLM 服务实例。
            model (str): 使用的模型名称。

        Returns:
            bool: 整合是否成功。
        """
        if not messages:
            return True

        current_memory = self.read_long_term()
        prompt = f"""Process this conversation and call the save_memory tool with your consolidation.

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{self._format_messages(messages)}"""

        chat_messages = [
            {"role": "system", "content": "You are a memory consolidation agent. Call the save_memory tool with your consolidation of the conversation."},
            {"role": "user", "content": prompt},
        ]

        try:
            forced = {"type": "function", "function": {"name": "save_memory"}}
            response = await provider.chat_with_retry(
                messages=chat_messages,
                tools=_SAVE_MEMORY_TOOL,
                model=model,
                tool_choice=forced,
            )

            # 如果强制 tool_choice 失败，尝试自动模式
            if response.finish_reason == "error" and _is_tool_choice_unsupported(
                response.content
            ):
                logger.warning("Forced tool_choice unsupported, retrying with auto")
                response = await provider.chat_with_retry(
                    messages=chat_messages,
                    tools=_SAVE_MEMORY_TOOL,
                    model=model,
                    tool_choice="auto",
                )

            if not response.has_tool_calls:
                logger.warning(
                    "Memory consolidation: LLM did not call save_memory "
                    "(finish_reason={}, content_len={}, content_preview={})",
                    response.finish_reason,
                    len(response.content or ""),
                    (response.content or "")[:200],
                )
                return self._fail_or_raw_archive(messages)

            # Access the first tool call
            # response.tool_calls is a list of objects or dicts depending on provider
            # Assuming LLMResponse normalizes it to list of objects with 'arguments' attribute or dict
            tc = response.tool_calls[0]
            if hasattr(tc, 'function'):
                 args_str = tc.function.arguments
            elif isinstance(tc, dict):
                 args_str = tc.get('function', {}).get('arguments', '{}')
            else:
                 # Fallback if structure is different
                 args_str = getattr(tc, 'arguments', '{}')

            args = _normalize_save_memory_args(args_str)

            if args is None:
                logger.warning("Memory consolidation: unexpected save_memory arguments")
                return self._fail_or_raw_archive(messages)

            if "history_entry" not in args or "memory_update" not in args:
                logger.warning("Memory consolidation: save_memory payload missing required fields")
                return self._fail_or_raw_archive(messages)

            entry = args["history_entry"]
            update = args["memory_update"]

            if entry is None or update is None:
                logger.warning("Memory consolidation: save_memory payload contains null required fields")
                return self._fail_or_raw_archive(messages)

            entry = _ensure_text(entry).strip()
            if not entry:
                logger.warning("Memory consolidation: history_entry is empty after normalization")
                return self._fail_or_raw_archive(messages)

            self.append_history(entry)
            update = _ensure_text(update)
            if update != current_memory:
                self.write_long_term(update)

            self._consecutive_failures = 0
            logger.info(f"Memory consolidation done for {len(messages)} messages")
            return True
        except Exception as e:
            logger.exception(f"Memory consolidation failed: {e}")
            return self._fail_or_raw_archive(messages)

    def _fail_or_raw_archive(self, messages: List[Dict]) -> bool:
        """
        增加失败计数；如果超过阈值，则对消息进行原始归档并返回 True。

        Args:
            messages (List[Dict]): 消息列表。

        Returns:
            bool: 如果已归档（无论成功与否）返回 True，否则 False。
        """
        self._consecutive_failures += 1
        if self._consecutive_failures < self._MAX_FAILURES_BEFORE_RAW_ARCHIVE:
            return False
        self._raw_archive(messages)
        self._consecutive_failures = 0
        return True

    def _raw_archive(self, messages: List[Dict]) -> None:
        """
        降级方案：将原始消息转储到 HISTORY.md，不进行 LLM 总结。

        Args:
            messages (List[Dict]): 消息列表。
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.append_history(
            f"[{ts}] [RAW] {len(messages)} messages\n"
            f"{self._format_messages(messages)}"
        )
        logger.warning(
            f"Memory consolidation degraded: raw-archived {len(messages)} messages"
        )


class MemoryConsolidator:
    """
    记忆整合协调器。
    负责整合策略、锁定和会话偏移更新。
    """

    _MAX_CONSOLIDATION_ROUNDS = 5

    def __init__(
        self,
        workspace: Path,
        provider: LLMService,
        model: str,
        sessions: SessionManager,
        context_window_tokens: int,
        build_messages: Callable[..., List[Dict[str, Any]]],
        get_tool_definitions: Callable[[], List[Dict[str, Any]]],
    ):
        """
        初始化 MemoryConsolidator。

        Args:
            workspace (Path): 工作区路径。
            provider (LLMService): LLM 服务提供者。
            model (str): 模型名称。
            sessions (SessionManager): 会话管理器。
            context_window_tokens (int): 上下文窗口大小。
            build_messages (Callable): 构建消息的函数。
            get_tool_definitions (Callable): 获取工具定义的函数。
        """
        self.store = MemoryStore(workspace)
        self.provider = provider
        self.model = model
        self.sessions = sessions
        self.context_window_tokens = context_window_tokens
        self._build_messages = build_messages
        self._get_tool_definitions = get_tool_definitions
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    def get_lock(self, session_key: str) -> asyncio.Lock:
        """
        获取指定会话的整合锁。

        Args:
            session_key (str): 会话键。

        Returns:
            asyncio.Lock: 会话锁。
        """
        return self._locks.setdefault(session_key, asyncio.Lock())

    async def consolidate_messages(self, messages: List[Dict[str, object]]) -> bool:
        """
        将选定的消息块归档到持久化记忆中。

        Args:
            messages (List[Dict[str, object]]): 消息列表。

        Returns:
            bool: 成功返回 True。
        """
        return await self.store.consolidate(messages, self.provider, self.model)

    def pick_consolidation_boundary(
        self,
        session: Session,
        tokens_to_remove: int,
    ) -> Optional[Tuple[int, int]]:
        """
        选择一个用户轮次边界，以移除足够多的旧提示词 token。

        Args:
            session (Session): 当前会话。
            tokens_to_remove (int): 需要移除的 token 数量。

        Returns:
            Optional[Tuple[int, int]]: (边界索引, 移除的 token 数) 或 None。
        """
        start = session.last_consolidated
        if start >= len(session.messages) or tokens_to_remove <= 0:
            return None

        removed_tokens = 0
        last_boundary: Optional[Tuple[int, int]] = None
        for idx in range(start, len(session.messages)):
            message = session.messages[idx]
            if idx > start and message.get("role") == "user":
                last_boundary = (idx, removed_tokens)
                if removed_tokens >= tokens_to_remove:
                    return last_boundary
            removed_tokens += estimate_message_tokens(message)

        return last_boundary

    def estimate_session_prompt_tokens(self, session: Session) -> Tuple[int, str]:
        """
        估算正常会话历史视图的当前提示词大小。

        Args:
            session (Session): 当前会话。

        Returns:
            Tuple[int, str]: (估算的 token 数, 调试信息)。
        """
        history = session.get_history(max_messages=100000)

        channel, chat_id = (session.key.split(":", 1) if ":" in session.key else (None, None))
        probe_messages = self._build_messages(
            history=history,
            current_message="[token-probe]",
            channel=channel,
            chat_id=chat_id,
        )
        return estimate_prompt_tokens_chain(
            self.provider,
            self.model,
            probe_messages,
            self._get_tool_definitions(),
        )

    async def archive_messages(self, messages: List[Dict[str, object]]) -> bool:
        """
        归档消息，保证持久化（重试直到降级为原始转储）。

        Args:
            messages (List[Dict[str, object]]): 消息列表。

        Returns:
            bool: 总是返回 True（因为有降级机制）。
        """
        if not messages:
            return True
        for _ in range(self.store._MAX_FAILURES_BEFORE_RAW_ARCHIVE):
            if await self.consolidate_messages(messages):
                return True
        return True
