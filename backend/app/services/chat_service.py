from typing import List, Dict, Any, Optional, Generator, AsyncGenerator
from sqlmodel import Session, select, col
from app.models.chat import ChatSession, ChatMessage
from app.models.attachment import Attachment
from app.service_client.agents_async_client import AgentsServiceAsyncClient
from app.service_client.models import (
    AgentMessageContract,
    AgentQueryRequestContract,
    ChatCompletionRequestContract,
)
from app.services.user_profile_service import user_profile_service
from app.services.storage_service import storage_service
import os
import uuid
import logging
import json
import base64
from datetime import datetime
import asyncio
from fastapi import Request

logger = logging.getLogger(__name__)

class ChatService:
    """
    聊天服务类，处理所有与聊天相关的业务逻辑。
    包括会话管理、消息发送、模型配置加载、事件广播等。
    """
    def __init__(self):
        """
        初始化 ChatService。
        加载模型配置并初始化事件监听器字典。
        """
        self.model_configs = []
        # session_id -> list of queues
        # 用于存储每个会话的 SSE 事件队列
        self.listeners: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue:
        """
        订阅指定会话的事件。
        为客户端创建一个新的异步队列，用于接收实时事件。

        Args:
            session_id (str): 会话 ID。

        Returns:
            asyncio.Queue: 用于接收事件的队列。
        """
        if session_id not in self.listeners:
            self.listeners[session_id] = []
        q = asyncio.Queue()
        self.listeners[session_id].append(q)
        return q

    def unsubscribe(self, session_id: str, q: asyncio.Queue):
        """
        取消订阅指定会话的事件。
        从监听器列表中移除指定的队列。

        Args:
            session_id (str): 会话 ID。
            q (asyncio.Queue): 要移除的队列。
        """
        if session_id in self.listeners:
            if q in self.listeners[session_id]:
                self.listeners[session_id].remove(q)
            # 如果该会话没有监听器了，清理字典条目
            if not self.listeners[session_id]:
                del self.listeners[session_id]

    async def broadcast_event(self, session_id: str, event_data: dict):
        """
        向指定会话的所有订阅者广播事件。

        Args:
            session_id (str): 会话 ID。
            event_data (dict): 事件数据。
        """
        if session_id in self.listeners:
            for q in self.listeners[session_id]:
                await q.put(event_data)



    async def get_enabled_models(self):
        """
        获取所有启用的模型配置。
        由于移除了本地的 model-config.json，改为向 agents 服务请求模型列表。

        Returns:
            list: 启用的模型配置列表。
        """
        try:
            client = AgentsServiceAsyncClient()
            headers = client._build_headers()
            response = await client.client.get("/api/v1/models", headers=headers)
            if response.status_code == 200:
                payload = response.json()
                source_models = payload if isinstance(payload, list) else payload.get("data", [])
                normalized_models = []
                for model in source_models:
                    if not isinstance(model, dict):
                        continue
                    model_id = model.get("id") or model.get("model") or model.get("name")
                    if not model_id:
                        continue
                    normalized_model_id = self._normalize_model_id(str(model_id))
                    normalized_models.append(
                        {
                            **model,
                            "id": normalized_model_id,
                            "name": model.get("name") or model.get("label") or normalized_model_id,
                            "enabled": model.get("enabled", True),
                        }
                    )
                enabled_models = [m for m in normalized_models if m.get("enabled", True)]
                if not any(model.get("id") == "deepseek/deepseek-chat" for model in enabled_models):
                    enabled_models.append(
                        {
                            "id": "deepseek/deepseek-chat",
                            "name": "DeepSeek Chat",
                            "enabled": True,
                        }
                    )
                if enabled_models:
                    return enabled_models
                logger.error("Agents service returned empty enabled models list")
            logger.error(
                "Failed to fetch models from agents service status=%s body=%s",
                response.status_code,
                response.text[:500],
            )
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
        fallback_model = os.getenv("AI_MODEL", "ollama/qwen3-vl:8b")
        return [
            {
                "id": self._normalize_model_id(fallback_model),
                "name": self._normalize_model_id(fallback_model),
                "enabled": True,
            },
            {
                "id": "deepseek/deepseek-chat",
                "name": "DeepSeek Chat",
                "enabled": True,
            }
        ]

    def _normalize_model_id(self, model_id: Optional[str]) -> str:
        if not model_id:
            return os.getenv("AI_MODEL", "ollama/qwen3-vl:8b")
        normalized = str(model_id).strip()
        if not normalized:
            return os.getenv("AI_MODEL", "ollama/qwen3-vl:8b")
        lower_model = normalized.lower()
        if lower_model in {"deepseek", "deepseek-chat"}:
            return "deepseek/deepseek-chat"
        if "/" in normalized:
            return normalized
        ollama_models = {
            "llama3",
            "qwen3-vl:8b",
            "qwen3-vl",
            "qwen2.5-coder:14b",
            "qwen2.5-coder",
            "mistral",
            "phi3",
        }
        if lower_model in ollama_models:
            return f"ollama/{normalized}"
        return normalized

    # ------------------------------------------------------------------
    # Debug breakpoint helper
    # ------------------------------------------------------------------
    def _dbp(self, tag: str, **fields) -> None:
        """Emit a structured DEBUG log line for a named breakpoint.

        Enable with LOG_LEVEL=DEBUG (or logger.setLevel(logging.DEBUG)).
        Each call produces one log line so grep/jq can filter per tag.

        Usage::
            self._dbp("BP-2", images_count=3, context_bytes=512)
        """
        if not logger.isEnabledFor(logging.DEBUG):
            return
        parts = " ".join(f"{k}={v!r}" for k, v in fields.items())
        logger.debug("[send_message:%s] %s", tag, parts)

    def _iter_text_chunks(self, text: str, chunk_size: int = 120) -> Generator[str, None, None]:
        normalized_text = str(text or "")
        if not normalized_text:
            return
        for index in range(0, len(normalized_text), chunk_size):
            yield normalized_text[index:index + chunk_size]

    async def _process_attachments(
        self,
        session: Session,
        images: Optional[List[str]],
        attachments: Optional[List[str]],
    ) -> tuple[list, str]:
        """
        Process raw images and attachment UUIDs into a usable form.

        Returns:
            processed_images: list of data-URL strings (original images + image attachments).
            attachment_context: concatenated file-content block for document attachments.
        """
        processed_images: list = list(images) if images else []
        attachment_context = ""

        if not attachments:
            return processed_images, attachment_context

        for attach_id in attachments:
            try:
                attachment = session.get(Attachment, attach_id)
                if not attachment:
                    continue

                file_path = storage_service.get_absolute_path(attachment.local_path)
                if not os.path.exists(file_path):
                    continue

                if attachment.mime_type.startswith("image/"):
                    with open(file_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                        data_url = f"data:{attachment.mime_type};base64,{encoded_string}"
                        processed_images.append(data_url)
                else:
                    extracted_text = await asyncio.to_thread(
                        self._extract_text_from_file, file_path, attachment.mime_type
                    )
                    if len(extracted_text) > 20000:
                        extracted_text = extracted_text[:20000] + "\n...(truncated)..."
                    attachment_context += (
                        f"\n\n[File Content: {attachment.original_name}]\n```\n{extracted_text}\n```\n"
                    )
            except Exception as e:
                logger.error(f"Error processing attachment {attach_id}: {e}")

        return processed_images, attachment_context

    def _build_message_context(
        self,
        session: Session,
        session_id: uuid.UUID,
        extra: Optional[dict],
        user_msg_id: Any,
        full_user_content: str,
    ) -> list:
        """
        Build the ordered messages list that will be sent to the AI provider.

        Injects an optional user-profile system message, then appends the
        conversation history (substituting the full content for the current
        user message).

        Returns:
            List of message dicts with keys: role, content, images.
        """
        history = self.get_messages(session, session_id)
        if extra and extra.get("ignore_history"):
            history = history[-1:] if history else []

        messages: list = []

        try:
            user_profile = user_profile_service.get_profile(session)
            if user_profile.identity or user_profile.rules:
                profile_prompt = "User Profile Context:\n"
                if user_profile.identity:
                    profile_prompt += f"Soul Identity: {user_profile.identity}\n"
                if user_profile.rules:
                    profile_prompt += f"Personal Rules: {user_profile.rules}\n"
                profile_prompt += "Please tailor your response based on this context."
                messages.append({"role": "system", "content": profile_prompt})
        except Exception as e:
            logger.error(f"Failed to inject user profile: {e}")

        for msg in history:
            msg_content = msg.get("content", "")
            if str(msg.get("id")) == str(user_msg_id):
                msg_content = full_user_content
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg_content,
                "images": msg.get("images", []),
            })

        return messages

    def _extract_send_options(self, extra: Optional[dict]) -> tuple[str, str, bool]:
        """
        Extract agent routing options from the ``extra`` request dict.

        Returns:
            agent_id: the agent to invoke (defaults to "MasterAgent").
            purpose: optional purpose string for routing hints.
            stage_progress_enabled: whether to stream reasoning-stage progress events.
        """
        agent_id = "MasterAgent"
        purpose = ""
        stage_progress_enabled = True

        if not isinstance(extra, dict):
            return agent_id, purpose, stage_progress_enabled

        agent_id = extra.get("agent_id") or "MasterAgent"
        purpose = str(extra.get("purpose", "")).strip().lower()

        stream_options = extra.get("stream_options")
        if isinstance(stream_options, dict):
            stage_progress_enabled = bool(stream_options.get("stage_progress_enabled", True))

        return agent_id, purpose, stage_progress_enabled

    def _build_agent_history_messages(self, messages: list) -> list:
        """
        Convert the message context list (excluding the last user message) into
        the ``AgentMessageContract`` format required by the agents service.

        Returns:
            List[AgentMessageContract]
        """
        history_messages = []
        for msg in messages[:-1]:
            role = msg.get("role", "user")
            if role not in {"system", "user", "assistant"}:
                continue
            history_messages.append(
                AgentMessageContract(
                    role=role,
                    content=msg.get("content", ""),
                    metadata={},
                )
            )
        return history_messages



    def create_session(self, session: Session, title: str = "New Chat") -> ChatSession:
        """
        创建一个新的聊天会话。

        Args:
            session (Session): 数据库会话。
            title (str): 会话标题，默认为 "New Chat"。

        Returns:
            ChatSession: 创建的会话对象。
        """
        chat_session = ChatSession(title=title)
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return chat_session

    def get_sessions(self, session: Session, limit: int = 20, offset: int = 0, query: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[ChatSession]:
        """
        获取聊天会话列表，支持分页、搜索和日期过滤。

        Args:
            session (Session): 数据库会话。
            limit (int): 限制数量。
            offset (int): 偏移量。
            query (Optional[str]): 搜索关键词（标题或消息内容）。
            start_date (Optional[datetime]): 起始日期。
            end_date (Optional[datetime]): 结束日期。

        Returns:
            List[ChatSession]: 会话列表。
        """
        statement = select(ChatSession).order_by(ChatSession.updated_at.desc())

        if query:
            # 关联查询消息表，匹配标题或消息内容
            statement = statement.join(ChatMessage).where(
                (col(ChatSession.title).contains(query)) | (col(ChatMessage.content).contains(query))
            ).distinct()

        if start_date:
            statement = statement.where(ChatSession.updated_at >= start_date)
        if end_date:
            statement = statement.where(ChatSession.updated_at <= end_date)

        statement = statement.offset(offset).limit(limit)
        return session.exec(statement).all()

    def get_session(self, session: Session, session_id: uuid.UUID) -> Optional[ChatSession]:
        """
        根据 ID 获取单个会话。

        Args:
            session (Session): 数据库会话。
            session_id (uuid.UUID): 会话 ID。

        Returns:
            Optional[ChatSession]: 会话对象，如果不存在则返回 None。
        """
        return session.get(ChatSession, session_id)

    def get_or_create_qqbot_session(self, session: Session) -> ChatSession:
        """
        获取或创建 QQBot 专用会话。
        该会话有一个固定的 share_id "fixed-qqbot-session"。

        Args:
            session (Session): 数据库会话。

        Returns:
            ChatSession: QQBot 会话对象。
        """
        from sqlmodel import select
        statement = select(ChatSession).where(ChatSession.share_id == "fixed-qqbot-session")
        chat_session = session.exec(statement).first()
        if not chat_session:
            chat_session = ChatSession(title="QQBot 协同会话", share_id="fixed-qqbot-session")
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
        return chat_session

    def delete_session(self, session: Session, session_id: uuid.UUID):
        """
        删除指定的会话。

        Args:
            session (Session): 数据库会话。
            session_id (uuid.UUID): 会话 ID。

        Returns:
            bool: 是否删除成功。
        """
        chat_session = session.get(ChatSession, session_id)
        if chat_session:
            session.delete(chat_session)
            session.commit()
            return True
        return False

    def update_session_title(self, session: Session, session_id: uuid.UUID, title: str) -> Optional[ChatSession]:
        """
        更新会话标题。

        Args:
            session (Session): 数据库会话。
            session_id (uuid.UUID): 会话 ID。
            title (str): 新标题。

        Returns:
            Optional[ChatSession]: 更新后的会话对象。
        """
        chat_session = session.get(ChatSession, session_id)
        if chat_session:
            chat_session.title = title
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
        return chat_session

    def get_messages(self, session: Session, session_id: uuid.UUID) -> List[Any]:
        """
        获取指定会话的所有消息，按创建时间排序，并包含附件详细信息。

        Args:
            session (Session): 数据库会话。
            session_id (uuid.UUID): 会话 ID。

        Returns:
            List[Any]: 消息列表。
        """
        from app.models.attachment import Attachment
        statement = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
        messages = session.exec(statement).all()

        result = []
        for msg in messages:
            msg_dict = msg.model_dump()
            if msg.attachments:
                att_objs = []
                for att_uuid in msg.attachments:
                    att = session.exec(select(Attachment).where(Attachment.uuid == att_uuid)).first()
                    if att:
                        att_objs.append({
                            "uuid": att.uuid,
                            "original_name": att.original_name,
                            "size": att.size,
                            "mime_type": att.mime_type,
                            "created_at": att.created_at.isoformat() if att.created_at else None
                        })
                msg_dict["attachment_objs"] = att_objs
            result.append(msg_dict)

        return result

    def _extract_text_from_file(self, file_path: str, mime_type: str) -> str:
        """
        Extract text from file based on mime type.
        Supports: pdf, docx, xlsx, txt, code.
        """
        try:
            if not os.path.exists(file_path):
                return "File not found."

            # PDF
            if mime_type == "application/pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text.strip()
                except ImportError:
                    return "Error: pypdf library not installed."
                except Exception as e:
                    return f"Error reading PDF: {str(e)}"

            # Word (docx)
            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                try:
                    import docx
                    doc = docx.Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    return text.strip()
                except ImportError:
                    return "Error: python-docx library not installed."
                except Exception as e:
                    return f"Error reading DOCX: {str(e)}"

            # Excel (xlsx)
            elif mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                try:
                    import pandas as pd
                    # Read all sheets
                    dfs = pd.read_excel(file_path, sheet_name=None)
                    text = ""
                    for sheet_name, df in dfs.items():
                        text += f"Sheet: {sheet_name}\n"
                        text += df.to_string() + "\n\n"
                    return text.strip()
                except ImportError:
                    return "Error: pandas or openpyxl library not installed."
                except Exception as e:
                    return f"Error reading XLSX: {str(e)}"

            # CSV
            elif mime_type == "text/csv":
                 try:
                    import pandas as pd
                    df = pd.read_csv(file_path)
                    return df.to_string()
                 except Exception as e:
                     return f"Error reading CSV: {str(e)}"

            # Text/Code
            elif mime_type.startswith("text/") or mime_type in ["application/json", "application/javascript", "application/xml", "application/x-sh", "application/x-python-code"]:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()

            else:
                return f"Unsupported file type: {mime_type}"

        except Exception as e:
            return f"Error extracting text: {str(e)}"

    async def send_message(self, session: Session, session_id: uuid.UUID, content: str, model_id: str, images: List[str] = None, attachments: List[str] = None, extra: dict = None) -> AsyncGenerator[str, None]:
        """
        发送消息的核心逻辑。
        1. 保存用户消息。
        2. 广播用户消息。
        3. 获取 AI 提供者。
        4. 构造历史上下文（包括系统提示词和用户资料）。
        5. 调用 AI 提供者生成流式响应。
        6. 保存助手消息。
        7. 广播助手消息。

        Args:
            session (Session): 数据库会话。
            session_id (uuid.UUID): 会话 ID。
            content (str): 用户消息内容。
            model_id (str): 模型 ID。
            images (List[str]): 图片列表。
            attachments (List[str]): 附件 UUID 列表。
            extra (dict): 额外信息。

        Yields:
            str: AI 生成的流式内容（JSON 格式或文本）。
        """
        # Ensure session_id is a valid UUID object
        if isinstance(session_id, str):
            try:
                session_id = uuid.UUID(session_id)
            except ValueError:
                pass

        # ── BP-1: session lookup ───────────────────────────────────
        chat_session = session.get(ChatSession, session_id)
        if not chat_session:
            raise ValueError("Session not found")

        # ── BP-2: attachment processing ────────────────────────────
        processed_images, attachment_context = await self._process_attachments(session, images, attachments)
        full_user_content = content + attachment_context

        # ── BP-3: save user message ────────────────────────────────
        try:
            user_msg = ChatMessage(
                session_id=session_id,
                role="user",
                content=content,
                images=processed_images,
                attachments=attachments,
                extra=extra
            )
            session.add(user_msg)
            session.commit()
            session.refresh(user_msg)

            msg_dict = {
                "id": str(user_msg.id),
                "role": user_msg.role,
                "content": user_msg.content,
                "created_at": user_msg.created_at.isoformat(),
                "extra": user_msg.extra,
                "images": user_msg.images,
                "attachments": user_msg.attachments
            }
            try:
                await self.broadcast_event(str(session_id), {"type": "new_message", "message": msg_dict})
            except Exception as e:
                logger.error(f"Failed to broadcast user message: {e}")

        except Exception as e:
            logger.error(f"Failed to save user message: {e}")
            session.rollback()
            yield f"Error: Failed to save message to database. {str(e)}\n"
            return

        # Release all ORM-bound objects from the injected session so the
        # connection is not held open across the streaming phase.
        session.expunge_all()

        client = AgentsServiceAsyncClient()

        try:
            # ── BP-5: message context built ────────────────────────
            messages = self._build_message_context(
                session, session_id, extra, user_msg.id, full_user_content
            )
            has_profile_msg = bool(messages and messages[0].get("role") == "system")
            self._dbp(
                "BP-5:message_context",
                total_messages=len(messages),
                has_profile_system_msg=has_profile_msg,
                ignore_history=bool(extra and extra.get("ignore_history")),
            )

            normalized_model_id = self._normalize_model_id(model_id)
            full_content = ""
            full_reasoning = ""
            assistant_extra = None

            # ── BP-6: routing options ──────────────────────────────
            selected_agent_id, selected_purpose, stage_progress_enabled = self._extract_send_options(extra)
            self._dbp(
                "BP-6:send_options",
                agent_id=selected_agent_id,
                purpose=selected_purpose,
                stage_progress_enabled=stage_progress_enabled,
                route="agent" if (selected_agent_id or selected_purpose) else "direct",
            )

            # selected_agent_id默认值会一直是MasterAgent
            if selected_agent_id or selected_purpose:
                yield json.dumps(
                    {
                        "reasoning": "正在调用 Agent 路由并生成回复...",
                        "metadata": {"stream_stage": "routing"},
                    },
                    ensure_ascii=False,
                ) + "\n"

                # ── BP-7: agent request built ──────────────────────
                history_messages = self._build_agent_history_messages(messages)
                self._dbp("BP-7:agent_history", history_count=len(history_messages))

                query_request = AgentQueryRequestContract(
                    query=full_user_content,
                    session_id=str(session_id),
                    history=history_messages,
                    parameters={
                        "agent_name": selected_agent_id,
                        "model_version": normalized_model_id,
                        "purpose": selected_purpose,
                    },
                )
                query_task = asyncio.create_task(client.query(query_request))
                wait_seconds = 0
                try:
                    while not query_task.done():
                        await asyncio.sleep(0.35)
                        wait_seconds += 0.35
                    query_response = await query_task
                except asyncio.CancelledError:
                    if not query_task.done():
                        query_task.cancel()
                    raise

                # ── BP-9: agent response received ──────────────────
                # Update selected_agent_id to reflect the agent that actually processed the request
                selected_agent_id = query_response.source_agent or selected_agent_id
                self._dbp(
                    "BP-9:agent_response",
                    wait_seconds=round(wait_seconds, 2),
                    has_error=bool(query_response.error),
                    answer_len=len(query_response.answer or ""),
                    source_agent=query_response.source_agent,
                    actual_agent_id=selected_agent_id,
                    latency_ms=query_response.latency_ms,
                    metadata_keys=list(query_response.metadata.keys()) if isinstance(query_response.metadata, dict) else None,
                )
                if query_response.error:
                    yield json.dumps({"error": query_response.error}) + "\n"
                    return

                full_content = query_response.answer or ""
                reasoning_trace = []
                routing_meta = {}
                if isinstance(query_response.metadata, dict):
                    routing_candidate = query_response.metadata.get("routing")
                    if isinstance(routing_candidate, dict):
                        routing_meta = routing_candidate
                    trace_candidate = query_response.metadata.get("reasoning_trace")
                    if isinstance(trace_candidate, list):
                        reasoning_trace = [
                            str(item).strip()
                            for item in trace_candidate
                            if isinstance(item, str) and str(item).strip()
                        ]
                assistant_extra = {
                    "source_agent": selected_agent_id,
                    "latency_ms": query_response.latency_ms,
                    "routing": routing_meta,
                }

                # Yield an agent-selected event so the frontend knows the actual agent
                yield json.dumps(
                    {
                        "reasoning": f"已选择 Agent：{selected_agent_id}",
                        "metadata": {
                            **assistant_extra,
                            "stream_stage": "agent_selected",
                        },
                    },
                    ensure_ascii=False,
                ) + "\n"

                if reasoning_trace:
                    reasoning_text = "\n\n".join(reasoning_trace)
                    full_reasoning = reasoning_text
                    reasoning_chunks = list(self._iter_text_chunks(reasoning_text, chunk_size=120))
                    for reasoning_chunk in reasoning_chunks:
                        yield json.dumps(
                            {
                                "reasoning": reasoning_chunk,
                                "metadata": {
                                    **assistant_extra,
                                    "stream_stage": "reasoning",
                                },
                            },
                            ensure_ascii=False,
                        ) + "\n"

                content_chunks = list(self._iter_text_chunks(full_content, chunk_size=120))
                for content_chunk in content_chunks:
                    yield json.dumps(
                        {
                            "content": content_chunk,
                            "reasoning": "",
                            "metadata": {
                                **assistant_extra,
                                "stream_stage": "final_answer",
                            },
                        },
                        ensure_ascii=False,
                    ) + "\n"
            else:
                # ── BP-7D: direct completion path ──────────────────
                # NOTE: structurally unreachable — _extract_send_options always
                # returns "MasterAgent" as default agent_id.
                self._dbp("BP-7D:direct_path", model=normalized_model_id)
                request_contract = ChatCompletionRequestContract(
                    messages=messages,
                    model=normalized_model_id,
                    stream=True,
                    temperature=0.7,
                    max_tokens=4096,
                    extra_params={"session_id": str(session_id)}
                )

                stream = client.chat_completion_stream(request_contract)
                direct_chunk_count = 0
                async for chunk_str in stream:
                    try:
                        data = json.loads(chunk_str)
                        chunk_content = data.get("content", "")
                        reasoning = data.get("reasoning", "")

                        if chunk_content:
                            full_content += chunk_content
                            data["metadata"] = {
                                **(data.get("metadata") if isinstance(data.get("metadata"), dict) else {}),
                                "stream_stage": "final_answer",
                            }
                        if reasoning:
                            full_reasoning += reasoning
                            if not chunk_content:
                                data["metadata"] = {
                                    **(data.get("metadata") if isinstance(data.get("metadata"), dict) else {}),
                                    "stream_stage": "reasoning",
                                }
                        direct_chunk_count += 1

                        yield json.dumps(data, ensure_ascii=False) + "\n"
                    except json.JSONDecodeError:
                        direct_chunk_count += 1
                        if chunk_str.startswith("Error:"):
                            yield json.dumps({"error": chunk_str}) + "\n"
                        else:
                            full_content += chunk_str
                            yield json.dumps({"content": chunk_str}) + "\n"

            # ── BP-11: assemble final content ──────────────────────
            final_content = full_content
            if full_reasoning:
                final_content = f"<think>\n{full_reasoning}\n</think>\n\n{full_content}"

            # ── BP-12: save assistant message (new session) ────────
            from app.core.database import engine as _engine
            with Session(_engine) as post_session:
                assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=final_content, extra=assistant_extra)
                post_session.add(assistant_msg)

                chat_session_post = post_session.get(ChatSession, session_id)
                if chat_session_post:
                    chat_session_post.updated_at = assistant_msg.created_at
                    post_session.add(chat_session_post)

                post_session.commit()
                post_session.refresh(assistant_msg)

            # Broadcast assistant message (广播助手消息事件)
            msg_dict = {
                "id": str(assistant_msg.id),
                "role": assistant_msg.role,
                "content": assistant_msg.content,
                "created_at": assistant_msg.created_at.isoformat(),
                "extra": assistant_msg.extra
            }
            try:
                await self.broadcast_event(str(session_id), {"type": "new_message", "message": msg_dict})
            except Exception as e:
                logger.error(f"Failed to broadcast assistant message: {e}")

        except Exception as e:
            logger.error(f"Error calling AI provider: {e}")
            yield f"Error: {str(e)}\n"

    def update_message_feedback(self, session: Session, message_id: uuid.UUID, feedback: Optional[str]) -> Optional[ChatMessage]:
        """
        更新消息的反馈状态（点赞/点踩）。

        业务逻辑：
        1. 根据 message_id 从数据库中查找对应的聊天消息记录。
        2. 如果消息存在，则更新其 feedback 字段。
        3. 将更改提交到数据库并刷新对象以获取最新状态。

        Args:
            session (Session): 数据库会话，用于执行数据库交互。
            message_id (uuid.UUID): 需要更新的聊天消息的唯一标识。
            feedback (Optional[str]): 反馈内容，通常为 "like" (点赞), "dislike" (点踩) 或 None (取消反馈)。

        Returns:
            Optional[ChatMessage]: 更新成功后的消息对象；如果未找到消息则返回 None。
        """
        msg = session.get(ChatMessage, message_id)
        if msg:
            msg.feedback = feedback
            session.add(msg)
            session.commit()
            session.refresh(msg)
        return msg

    def update_message_favorite(self, session: Session, message_id: uuid.UUID, is_favorite: bool) -> Optional[ChatMessage]:
        """
        更新消息的收藏状态。

        业务逻辑：
        1. 根据 message_id 从数据库中检索目标聊天消息。
        2. 如果找到该消息，将其 is_favorite 字段更新为传入的布尔值。
        3. 提交数据库事务并刷新消息对象。

        Args:
            session (Session): 数据库会话，负责管理数据库连接和事务。
            message_id (uuid.UUID): 目标聊天消息的唯一 ID。
            is_favorite (bool): 表示是否收藏该消息的布尔标志（True 表示收藏，False 表示取消收藏）。

        Returns:
            Optional[ChatMessage]: 状态更新后的聊天消息对象；如果目标消息不存在则返回 None。
        """
        msg = session.get(ChatMessage, message_id)
        if msg:
            msg.is_favorite = is_favorite
            session.add(msg)
            session.commit()
            session.refresh(msg)
        return msg

    def share_session(self, session: Session, session_id: uuid.UUID) -> Optional[str]:
        """
        为指定的聊天会话生成用于公开分享的链接 ID。

        业务逻辑：
        1. 通过 session_id 在数据库中查询对应的聊天会话。
        2. 如果会话存在且尚未生成 share_id，则生成一个新的 UUID 字符串作为其 share_id。
        3. 将新生成的 share_id 保存到数据库中。
        4. 如果会话已经存在 share_id，则直接返回已有的 ID。

        Args:
            session (Session): 数据库会话对象。
            session_id (uuid.UUID): 需要分享的聊天会话 ID。

        Returns:
            Optional[str]: 用于分享的唯一字符串 ID；如果未找到对应的会话则返回 None。
        """
        chat_session = session.get(ChatSession, session_id)
        if chat_session:
            if not chat_session.share_id:
                chat_session.share_id = str(uuid.uuid4())
                session.add(chat_session)
                session.commit()
                session.refresh(chat_session)
            return chat_session.share_id
        return None

    def get_shared_session(self, session: Session, share_id: str):
        """
        根据分享 ID 获取对应的公开聊天会话及其所有历史消息。

        业务逻辑：
        1. 在数据库的 ChatSession 表中根据 share_id 进行精确查询。
        2. 如果匹配到会话，则调用 get_messages 方法获取该会话下的所有历史消息记录。
        3. 将会话对象和关联的消息列表组装成字典返回。

        Args:
            session (Session): 数据库会话依赖，用于执行数据查询。
            share_id (str): 会话分享时生成的唯一分享标识符。

        Returns:
            dict: 包含 "session" (ChatSession 对象) 和 "messages" (ChatMessage 对象列表) 的字典。
                  如果未能通过 share_id 找到任何会话，则返回 None。
        """
        from sqlmodel import select
        statement = select(ChatSession).where(ChatSession.share_id == share_id)
        chat_session = session.exec(statement).first()
        if chat_session:
            messages = self.get_messages(session, chat_session.id)
            return {
                "session": chat_session,
                "messages": messages
            }
        return None

# 全局 ChatService 实例
chat_service = ChatService()
