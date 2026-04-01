"""
会话管理模块，负责管理对话历史记录。
该模块提供了 Session 类用于封装单个会话的状态和消息，
以及 SessionManager 类用于处理会话的持久化存储（加载和保存）。
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging
from utils.utils import ensure_dir, safe_filename

logger = logging.getLogger(__name__)

@dataclass
class Session:
    """
    对话会话类。
    维护一个特定会话的所有消息记录和元数据。
    数据结构设计为易于序列化为 JSONL 格式。
    """

    key: str  # 会话的唯一标识符 (通常格式为 channel:chat_id)
    messages: List[Dict[str, Any]] = field(default_factory=list) # 消息列表，存储所有对话记录
    created_at: datetime = field(default_factory=datetime.now) # 会话创建时间
    updated_at: datetime = field(default_factory=datetime.now) # 会话最后更新时间
    metadata: Dict[str, Any] = field(default_factory=dict) # 会话元数据（如用户信息、偏好设置等）
    last_consolidated: int = 0  # 记录已合并到长期记忆文件的消息数量索引，避免重复处理

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """
        向当前会话追加一条新消息。
        会自动添加当前时间戳。

        Args:
            role (str): 消息发送者角色 (user, assistant, system, tool)。
            content (str): 消息的具体文本内容。
            **kwargs: 其他需要存储的字段（如 tool_calls, tool_call_id 等）。
        """
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(), # 使用 ISO 格式记录时间
            **kwargs
        }
        self.messages.append(msg)
        self.updated_at = datetime.now() # 更新会话最后活跃时间

    @staticmethod
    def _find_legal_start(messages: List[Dict[str, Any]]) -> int:
        """
        查找消息列表中第一个“合法”的起始索引。

        背景：在截断历史记录时，可能会不小心切断了 'assistant' 发起工具调用 (tool_calls)
        和 'tool' 返回结果 (tool) 之间的联系。
        许多 LLM 提供商（如 OpenAI, Anthropic）如果收到一个没有对应 'assistant' tool_calls
        的孤立 'tool' 消息，会报错。

        此方法用于扫描消息列表，确保如果包含 'tool' 消息，它之前的 'assistant' 消息也在列表中。
        如果发现孤立的 'tool' 消息，则向前跳过，直到找到一个合法的起点。

        Args:
            messages (List[Dict[str, Any]]): 待检查的消息列表片段。

        Returns:
            int: 建议的切片起始索引。
        """
        declared = set() # 记录已看到的 tool_call_id
        start = 0
        for i, msg in enumerate(messages):
            role = msg.get("role")
            if role == "assistant":
                # 收集 assistant 声明的所有 tool_calls ID
                for tc in msg.get("tool_calls") or []:
                    if isinstance(tc, dict) and tc.get("id"):
                        declared.add(str(tc["id"]))
            elif role == "tool":
                # 检查 tool 消息的 ID 是否在之前声明过
                tid = msg.get("tool_call_id")
                # 如果这是一个未声明的 tool 消息（即孤儿消息）
                if tid and str(tid) not in declared:
                    # 这意味着对应的 assistant 消息在切片之外，这个 tool 消息是非法的
                    # 我们必须丢弃包括这条在内的之前所有消息，从下一条开始尝试
                    start = i + 1
                    declared.clear() # 重置已声明集合，因为我们丢弃了上下文
                    # 重新扫描从新起点到当前位置之间的 assistant 消息（如果有的话），
                    # 虽然在这个逻辑分支下，start = i + 1，所以这里实际上是为下一次循环做准备
                    # 但为了逻辑严谨，如果回溯检查是必要的（当前逻辑其实是简单的丢弃策略）

                    # 修正逻辑说明：上面的代码实际上是重新扫描 [start, i+1] 范围，
                    # 但因为 start 刚被设为 i+1，这个循环是空的。
                    # 真正的目的是：如果未来还有 tool 消息，它们需要匹配 start 之后出现的 assistant 消息。
                    pass
        return start

    def get_history(self, max_messages: int = 500) -> List[Dict[str, Any]]:
        """
        获取用于 LLM 上下文输入的历史消息列表。
        执行以下操作：
        1. 仅获取尚未被“合并/归档”的消息（由 last_consolidated 控制）。
        2. 根据 max_messages 限制返回的消息数量。
        3. 确保返回的消息列表以 User 消息或 System 消息（如果策略允许）开头，
           避免从对话中间截断导致上下文缺失。
        4. 确保工具调用的完整性（Assistant tool_calls 和 Tool result 成对出现）。

        Args:
            max_messages (int): 返回的最大消息条数。

        Returns:
            List[Dict[str, Any]]: 清洗和格式化后的消息列表。
        """
        # 1. 获取未归档的消息
        unconsolidated = self.messages[self.last_consolidated:]

        # 2. 应用数量限制
        if max_messages > 0:
            sliced = unconsolidated[-max_messages:]
        else:
            sliced = unconsolidated

        # 3. 启发式调整：丢弃开头的非用户消息
        # 避免从 Assistant 的回复中间开始，导致 LLM 困惑
        # 我们尝试找到第一个 "user" 消息作为起点
        for i, message in enumerate(sliced):
            if message.get("role") == "user":
                sliced = sliced[i:]
                break

        # 4. 安全性检查：处理孤立的工具结果
        # 某些提供商会拒绝孤立的工具结果（如果匹配的 assistant tool_calls 消息在历史窗口之外）。
        start = self._find_legal_start(sliced)
        if start:
            sliced = sliced[start:]

        # 5. 格式化输出
        # 仅保留 LLM 真正需要的字段，去除内部元数据（如 timestamp）
        out: List[Dict[str, Any]] = []
        for message in sliced:
            entry: Dict[str, Any] = {"role": message["role"], "content": message.get("content", "")}
            # 复制工具调用相关的关键字段
            for key in ("tool_calls", "tool_call_id", "name"):
                if key in message:
                    entry[key] = message[key]
            out.append(entry)
        return out

    def clear(self) -> None:
        """
        清空会话的所有消息并重置状态。
        相当于开始一个新的对话，但保留会话 ID (key)。
        """
        self.messages = []
        self.last_consolidated = 0
        self.updated_at = datetime.now()


class SessionManager:
    """
    会话管理器。
    负责会话对象的创建、检索、加载和保存。
    会话数据以 JSONL 文件形式存储在工作区的 sessions 目录下。
    """

    def __init__(self, workspace: Path):
        """
        初始化 SessionManager。

        Args:
            workspace (Path): 根工作区路径，sessions 目录将创建在此路径下。
        """
        self.workspace = workspace
        self.sessions_dir = ensure_dir(self.workspace / "sessions")
        self._cache: Dict[str, Session] = {} # 内存缓存，避免频繁读取磁盘

    def _get_session_path(self, key: str) -> Path:
        """
        根据会话键生成对应的文件路径。
        会将键中的特殊字符（如冒号）替换为安全字符。

        Args:
            key (str): 会话键。

        Returns:
            Path: 对应的 JSONL 文件绝对路径。
        """
        safe_key = safe_filename(key.replace(":", "_"))
        return self.sessions_dir / f"{safe_key}.jsonl"

    def get_or_create(self, key: str) -> Session:
        """
        获取现有会话，如果不存在则创建一个新会话。
        优先从内存缓存获取，其次尝试从磁盘加载，最后新建。

        Args:
            key (str): 会话键 (通常为 channel:chat_id)。

        Returns:
            Session: 会话对象。
        """
        # 1. 检查缓存
        if key in self._cache:
            return self._cache[key]

        # 2. 尝试从磁盘加载
        session = self._load(key)

        # 3. 如果磁盘也没有，则新建
        if session is None:
            session = Session(key=key)

        # 存入缓存
        self._cache[key] = session
        return session

    def _load(self, key: str) -> Optional[Session]:
        """
        从磁盘加载会话数据。

        Args:
            key (str): 会话键。

        Returns:
            Optional[Session]: 加载成功的会话对象，如果文件不存在则返回 None。
        """
        path = self._get_session_path(key)

        if not path.exists():
            return None

        try:
            messages = []
            metadata = {}
            created_at = None
            last_consolidated = 0

            # 读取 JSONL 文件，每一行是一个 JSON 对象
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # 根据记录类型分发处理
                        if record.get("type") == "metadata":
                            metadata = record.get("data", {})
                        elif record.get("type") == "state":
                             # 加载状态信息（如 last_consolidated）
                            last_consolidated = record.get("data", {}).get("last_consolidated", 0)
                        elif record.get("role"):
                            # 这是一个消息记录
                            messages.append(record)
                            # 如果第一条消息包含时间戳，将其作为创建时间
                            if created_at is None and "timestamp" in record:
                                try:
                                    created_at = datetime.fromisoformat(record["timestamp"])
                                except ValueError:
                                    pass
                    except json.JSONDecodeError:
                        continue

            # 构建 Session 对象
            session = Session(
                key=key,
                messages=messages,
                metadata=metadata,
                last_consolidated=last_consolidated
            )
            if created_at:
                session.created_at = created_at

            return session

        except Exception as e:
            logger.error(f"Failed to load session {key}: {e}")
            return None

    def save(self, session: Session) -> None:
        """
        将会话保存到磁盘。
        采用全量重写的方式保存为 JSONL 格式。

        文件结构：
        1. metadata 行
        2. state 行
        3. message 行 (多行)

        Args:
            session (Session): 要保存的会话对象。
        """
        path = self._get_session_path(session.key)

        try:
            # 临时文件路径，用于原子写入
            temp_path = path.with_suffix(".tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                # 1. 写入元数据
                if session.metadata:
                    f.write(json.dumps({"type": "metadata", "data": session.metadata}, ensure_ascii=False) + "\n")

                # 2. 写入状态数据
                state_data = {
                    "last_consolidated": session.last_consolidated,
                    "updated_at": session.updated_at.isoformat()
                }
                f.write(json.dumps({"type": "state", "data": state_data}, ensure_ascii=False) + "\n")

                # 3. 写入消息列表
                for msg in session.messages:
                    # 确保 msg 是纯字典，不包含不可序列化的对象
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")

            # 原子移动：将临时文件重命名为目标文件
            shutil.move(temp_path, path)

        except Exception as e:
            logger.error(f"Failed to save session {session.key}: {e}")
