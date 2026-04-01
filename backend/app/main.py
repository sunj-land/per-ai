import logging
import os
import sys

# Add project root to sys.path to allow importing 'agents' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from app.core.database import create_db_and_tables, get_session
from app.core.logging_config import configure_logging, TraceIdMiddleware
from app.models.rss import RSSFeed, RSSArticle
from app.models.rss_quality import RSSQualityRule, RSSQualityScoreLog, RSSQualityScoreResult
from app.models.chat import ChatSession, ChatMessage
from app.models.note import ArticleNote, ArticleSummary
from app.models.user_profile import UserProfile
from app.models.task import Task
from app.models.channel import Channel, ChannelMessage
# --- Learning Agent Models ---
from app.models.user import User
from app.models.plan import PlanHeader, PlanMilestone, PlanTask
from app.models.content import ContentRepo
from app.models.progress import UserProgress, EventLog
from app.models.reminder import UserReminder
from app.models.attachment import Attachment
# -----------------------------

from app.api import rss, chat, note, user_profile, card_center, task, channel, agent, skill, agents, rss_quality
from app.api import auth, plan, content, progress, reminder, attachment, users, schedule, schedule_ai # New APIs

# 已经将 agents 独立，不再将 agents 服务路由直接注入到 backend
# from agents.api.service import router as agents_service_router
# from agents.api.endpoints import router as master_agent_router
from app.api.chat import router as chat_router # Import the new chat router
from app.api.channel import router as channel_router # Import the new channel router
# from app.api.tools import router as tools_router # Import the tools router

from app.services.rss_service import update_all_feeds_background
from app.services.task_service import task_service
from app.services.schedule_service import schedule_service
from app.services.learning_scheduler import learning_scheduler
from app.services.agent_center_catalog_service import agent_center_catalog_service
from app.core.scheduler import scheduler
from sqlmodel import Session, create_engine
from app.core.database import engine
from app.core.init_data import init_db
from app.core.bus.dispatcher import outbound_dispatcher

log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
configure_logging(log_dir)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

    # Initialize DB data
    with Session(engine) as session:
        init_db(session)

    # Initialize TaskService (loads tasks from DB)
    await task_service.initialize()

    # Schedule Daily Content Generation (e.g., 2 AM)
    scheduler.add_job(learning_scheduler.generate_daily_content, "cron", hour=2, minute=0)
    # Schedule Daily Reminders (e.g., 9 AM)
    scheduler.add_job(learning_scheduler.send_daily_reminders, "cron", hour=9, minute=0)

    # Schedule Schedule Reminders (Every minute)
    scheduler.add_job(schedule_service.check_and_send_reminders, "interval", minutes=1)

    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started.")

    # Start message bus loops
    outbound_dispatcher.start()
    logger.info("Message bus loops started.")

    try:
        agent_center_catalog_service.initialize()
        logger.info("Agent center catalog service initialized.")
    except Exception as exc:
        logger.exception("Agent center catalog service initialize failed: %s", exc)

    yield

    # Stop message bus loops
    outbound_dispatcher.stop()
    logger.info("Message bus loops stopped.")

    try:
        agent_center_catalog_service.shutdown()
        logger.info("Agent center catalog service shutdown.")
    except Exception as exc:
        logger.exception("Agent center catalog service shutdown failed: %s", exc)

    scheduler.shutdown()
    logger.info("Scheduler shutdown.")

app = FastAPI(
    title="企业级项目后端 API",
    description="""
    这是基于 FastAPI 构建的企业级项目后端 API 文档。

    主要功能包括：
    * **RSS 订阅管理**: 支持 RSS/Atom 源的添加、查询和自动更新。
    * **文章阅读**: 提供文章列表查询和详情查看功能。
    """,
    version="0.1.0",
    openapi_tags=[
        {
            "name": "RSS",
            "description": "RSS 订阅源和文章相关的操作接口",
        },
        {
            "name": "Root",
            "description": "系统基础接口",
        },
        {
            "name": "UserProfile",
            "description": "用户个人信息管理接口",
        },
    ],
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TraceIdMiddleware)

@app.get("/health", tags=["Root"])
async def health():
    return {"status": "ok"}


@app.get("/agents/health", tags=["Root"])
async def agents_health():
    return {"status": "ok"}

app.include_router(rss.router, prefix="/api/v1/rss", tags=["RSS"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(note.router, prefix="/api/v1/notes", tags=["Note"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents Proxy"])
app.include_router(user_profile.router, prefix="/api/v1/profile", tags=["UserProfile"])
app.include_router(card_center.router, prefix="/api/v1/cards", tags=["CardCenter"])
app.include_router(task.router, prefix="/api/v1/tasks", tags=["Task"])
app.include_router(agent.router, prefix="/api/v1/agent-center/agents", tags=["Agent"])
app.include_router(skill.router, prefix="/api/v1/agent-center/skills", tags=["Skill"])
app.include_router(rss_quality.router, prefix="/api/v1/agent-center/rss-quality", tags=["RSS Quality"])
# app.include_router(channel.router, prefix="/api/v1/channels", tags=["Channel"])
app.include_router(channel_router, prefix="/api/v1/channels", tags=["Channel"]) # Include the new channel router
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(plan.router, prefix="/api/v1/plans", tags=["Plan"])
app.include_router(content.router, prefix="/api/v1/content", tags=["Content"])
app.include_router(progress.router, prefix="/api/v1/progress", tags=["Progress"])
app.include_router(reminder.router, prefix="/api/v1/reminders", tags=["Reminders"])
app.include_router(attachment.router, prefix="/api/v1/attachments", tags=["Attachments"])
app.include_router(schedule.router, prefix="/api/v1/schedules", tags=["Schedules"])
app.include_router(schedule_ai.router, prefix="/api/v1/schedule-ai", tags=["Schedule AI"])
# app.include_router(tools_router, prefix="/api/v1/tools", tags=["Tools"])
# app.include_router(agents_service_router, prefix="/api/v1", tags=["Unified LLM Service"])
# app.include_router(master_agent_router, prefix="/api/v1/agents", tags=["Master Agent"])

# Frontend Static Files
# backend/app/main.py -> backend/app -> backend -> root
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "packages", "web", "dist")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Check if file exists in dist (e.g. vite.svg, favicon.ico)
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Otherwise return index.html for SPA routing
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
