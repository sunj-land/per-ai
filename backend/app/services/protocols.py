"""
Service interface contracts defined as typing.Protocol classes.

These provide stable contracts for services that are called from multiple
call sites, enabling type-checker validation and easier testing via mocks.
"""
from __future__ import annotations

import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Protocol, runtime_checkable

from sqlmodel import Session


@runtime_checkable
class ChatServiceProtocol(Protocol):
    """Contract for ChatService."""

    def create_session(self, session: Session, title: str = "New Chat") -> Any: ...

    def get_sessions(
        self,
        session: Session,
        limit: int = 20,
        offset: int = 0,
        query: Optional[str] = None,
        start_date: Any = None,
        end_date: Any = None,
    ) -> List[Any]: ...

    def get_session(self, session: Session, session_id: uuid.UUID) -> Optional[Any]: ...

    def delete_session(self, session: Session, session_id: uuid.UUID) -> bool: ...

    def update_session_title(
        self, session: Session, session_id: uuid.UUID, title: str
    ) -> Optional[Any]: ...

    def get_messages(self, session: Session, session_id: uuid.UUID) -> List[Any]: ...

    async def send_message(
        self,
        session: Session,
        session_id: uuid.UUID,
        content: str,
        model_id: str,
        images: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        extra: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]: ...

    async def get_enabled_models(self) -> List[Dict[str, Any]]: ...

    def subscribe(self, session_id: str) -> Any: ...

    def unsubscribe(self, session_id: str, q: Any) -> None: ...

    async def broadcast_event(self, session_id: str, event_data: dict) -> None: ...

    def share_session(self, session: Session, session_id: uuid.UUID) -> Optional[str]: ...

    def get_shared_session(self, session: Session, share_id: str) -> Optional[dict]: ...

    def update_message_feedback(
        self, session: Session, message_id: uuid.UUID, feedback: Optional[str]
    ) -> Optional[Any]: ...

    def update_message_favorite(
        self, session: Session, message_id: uuid.UUID, is_favorite: bool
    ) -> Optional[Any]: ...


@runtime_checkable
class TaskServiceProtocol(Protocol):
    """Contract for TaskService."""

    async def initialize(self) -> None: ...

    async def create_task(self, task_data: Any) -> Any: ...

    async def update_task(
        self, task_id: uuid.UUID, update_data: Dict[str, Any]
    ) -> Optional[Any]: ...

    async def delete_task(self, task_id: uuid.UUID) -> bool: ...

    async def pause_task(self, task_id: uuid.UUID) -> Optional[Any]: ...

    async def resume_task(self, task_id: uuid.UUID) -> Optional[Any]: ...

    async def execute_task(self, task_id: uuid.UUID) -> None: ...


@runtime_checkable
class ChannelServiceProtocol(Protocol):
    """Contract for ChannelService."""

    def create_channel(self, channel: Any) -> Any: ...

    def get_channels(self, skip: int = 0, limit: int = 100) -> List[Any]: ...

    def get_channel(self, channel_id: uuid.UUID) -> Optional[Any]: ...

    def update_channel(self, channel_id: uuid.UUID, channel: Any) -> Optional[Any]: ...

    def delete_channel(self, channel_id: uuid.UUID) -> bool: ...

    async def send_message(
        self, channel_id: uuid.UUID, content: str, title: Optional[str] = None
    ) -> Any: ...

    async def broadcast(self, content: str, title: Optional[str] = None) -> List[Any]: ...

    async def handle_webhook(self, channel_id: uuid.UUID, payload: dict) -> Any: ...


@runtime_checkable
class ScheduleServiceProtocol(Protocol):
    """Contract for ScheduleService."""

    async def create_schedule(self, schedule_in: Any) -> Any: ...

    async def get_schedules(
        self,
        start_time: Any = None,
        end_time: Any = None,
        keyword: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Any]: ...

    async def get_schedule(self, schedule_id: uuid.UUID) -> Optional[Any]: ...

    async def update_schedule(
        self, schedule_id: uuid.UUID, schedule_in: Any
    ) -> Optional[Any]: ...

    async def delete_schedule(self, schedule_id: uuid.UUID) -> bool: ...

    def backup_data(self) -> dict: ...

    def restore_data(self, data: dict, clear_existing: bool = False) -> None: ...
