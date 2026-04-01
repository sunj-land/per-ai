"""
Dependency factories for FastAPI Depends() injection.

All service singletons are exposed through getter functions rather than
being imported directly in route modules. This makes every call site
testable (swap the dependency in overrides) and makes coupling explicit.

Usage in a route:
    from app.core.dependencies import get_chat_service
    from app.services.protocols import ChatServiceProtocol

    @router.post("/send")
    async def send(svc: ChatServiceProtocol = Depends(get_chat_service)):
        ...
"""
from __future__ import annotations


def get_chat_service():
    from app.services.chat_service import chat_service
    return chat_service


def get_task_service():
    from app.services.task_service import task_service
    return task_service


def get_channel_service():
    from app.services.channel_service import channel_service
    return channel_service


def get_schedule_service():
    from app.services.schedule_service import schedule_service
    return schedule_service


def get_user_profile_service():
    from app.services.user_profile_service import user_profile_service
    return user_profile_service


def get_rss_quality_service():
    from app.services.rss_quality_service import rss_quality_service
    return rss_quality_service


def get_skill_service():
    from app.services.skill_service import skill_service
    return skill_service


def get_skill_install_progress_service():
    from app.services.skill_install_progress_service import skill_install_progress_service
    return skill_install_progress_service


def get_agent_center_catalog_service():
    from app.services.agent_center_catalog_service import agent_center_catalog_service
    return agent_center_catalog_service


def get_agent_service():
    from app.services.agent_service import agent_service
    return agent_service


def get_attachment_service():
    from app.services.attachment_service import attachment_service
    return attachment_service


def get_storage_service():
    from app.services.storage_service import storage_service
    return storage_service


def get_rss_group_service():
    from app.services.rss_group_service import RSSGroupService
    return RSSGroupService()


def get_ai_card_service():
    from app.services.ai_card_service import AICardService
    return AICardService()
