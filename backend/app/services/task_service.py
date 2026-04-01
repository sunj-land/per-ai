import logging
import asyncio
import subprocess
import httpx
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any, Callable
from sqlmodel import Session, select
from app.core.database import engine
from app.models.task import Task, TaskLog
from app.core.scheduler import scheduler
from app.services.rss_service import update_all_feeds_background
# from app.services.vector_service import vector_service
from fastapi.concurrency import run_in_threadpool

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 内部函数注册表，将字符串标识映射到实际的可执行函数
_FUNCTION_REGISTRY: Dict[str, Callable] = {}


def register_task_function(name: str):
    """
    装饰器：将函数注册到任务函数注册表中。
    使用方式: @register_task_function("key")
    """
    def decorator(func: Callable) -> Callable:
        _FUNCTION_REGISTRY[name] = func
        return func
    return decorator

@register_task_function("rss_fetch")
async def run_rss_and_vectorize():
    """
    运行 RSS 抓取及后续的向量化处理任务。
    此方法会被注册为系统内置的定时任务进行调度。
    """
    logger.info("Scheduled fetch started...")
    try:
        # ========== 步骤1：后台更新所有 RSS 源 ==========
        await run_in_threadpool(update_all_feeds_background)
        logger.info("RSS feeds updated.")
    except Exception as e:
        logger.error(f"Error updating RSS feeds: {e}")

    try:
        def run_vectorization():
            """
            同步执行向量化逻辑的内部函数，供线程池调用。
            :return: 处理的文章数量。
            """
            # with Session(engine) as session:
            #     return vector_service.vectorize_pending_articles(session)
            return 0

        # ========== 步骤2：对新获取的文章进行向量化处理 ==========
        count = await run_in_threadpool(run_vectorization)
        if count > 0:
            logger.info(f"Vectorized {count} new articles.")
    except Exception as e:
        logger.error(f"Error vectorizing articles: {e}")

    logger.info("Scheduled fetch completed.")

@register_task_function("push_random_article_to_qqbot")
async def push_random_article_to_qqbot():
    """
    随机从文章库选取一条文章，通过 QQBot 推送。
    """
    logger.info("Starting random article push to QQBot...")
    from app.models.rss import RSSArticle
    from app.models.channel import Channel
    from sqlalchemy.sql.expression import func
    from app.services.channel_service import ChannelService

    try:
        with Session(engine) as session:
            # 1. 获取随机文章
            article = session.exec(select(RSSArticle).order_by(func.random()).limit(1)).first()
            if not article:
                logger.warning("No articles found in the database. Skip push.")
                return

            # 2. 获取有效的 qqbot 渠道
            channel = session.exec(select(Channel).where(Channel.type == "qqbot", Channel.is_active == True).limit(1)).first()
            if not channel:
                logger.warning("No active QQBot channel found. Skip push.")
                return

            # 3. 构造消息内容
            content = f"【随机文章推荐】\n**{article.title}**\n\n"
            if article.summary:
                content += f"{article.summary[:200]}...\n\n"
            content += f"[阅读原文]({article.link})"

            # 4. 执行推送 (利用 ChannelService 的内建重试和日志机制)
            channel_svc = ChannelService()
            await channel_svc.send_message(channel.id, content=content, title="随机推荐")
            logger.info(f"Successfully pushed article '{article.title}' to QQBot.")
    except Exception as e:
        logger.error(f"Failed to push random article: {e}")
        raise e

class TaskService:
    """
    任务调度与管理服务类。
    负责任务的增删改查、初始化内置任务以及与 APScheduler 调度器的交互。
    """

    def __init__(self):
        """
        初始化任务服务，绑定全局调度器。
        """
        self.scheduler = scheduler

    async def initialize(self):
        """
        初始化服务：加载数据库中所有活跃任务并加入调度器。
        同时会确保系统中存在默认的 RSS 和 AI 任务，如果缺失则自动创建。
        """
        logger.info("Initializing TaskService...")
        with Session(engine) as session:
            # ========== 步骤1：检查并创建默认 RSS 任务 ==========
            rss_task = session.exec(select(Task).where(Task.name == "System RSS Fetch")).first()
            if not rss_task:
                rss_task = Task(
                    name="System RSS Fetch",
                    description="Automatically fetch RSS feeds every 30 minutes",
                    type="function",
                    payload="rss_fetch",
                    schedule_type="interval",
                    schedule_config={"minutes": 30},
                    is_active=True
                )
                session.add(rss_task)
                session.commit()
                session.refresh(rss_task)
                logger.info("Seeded default RSS task.")

            # ========== 步骤2：检查并创建默认 AI 激励任务 ==========
            ai_task = session.exec(select(Task).where(Task.name == "Daily Encouragement")).first()
            if not ai_task:
                ai_task = Task(
                    name="Daily Encouragement",
                    description="Get a daily motivational quote from AI",
                    type="ai_dialogue",
                    payload="Generate a short, inspiring quote for a software developer.",
                    schedule_type="interval",
                    schedule_config={"hours": 24},
                    is_active=True
                )
                session.add(ai_task)
                session.commit()
                session.refresh(ai_task)
                logger.info("Seeded default AI task.")

            # ========== 步骤3：检查并创建默认的随机文章推送任务 ==========
            random_push_task = session.exec(select(Task).where(Task.name == "Random Article Push")).first()
            if not random_push_task:
                random_push_task = Task(
                    name="Random Article Push",
                    description="Push a random article to QQBot every 5 minutes",
                    type="function",
                    payload="push_random_article_to_qqbot",
                    schedule_type="interval",
                    schedule_config={"minutes": 5},
                    is_active=True
                )
                session.add(random_push_task)
                session.commit()
                session.refresh(random_push_task)
                logger.info("Seeded default Random Article Push task.")

            # ========== 步骤4：加载所有活跃任务并进行调度 ==========
            tasks = session.exec(select(Task).where(Task.is_active == True)).all()
            for task in tasks:
                self._schedule_job(task)
        logger.info(f"Initialized {len(tasks)} tasks.")

    def _schedule_job(self, task: Task):
        """
        根据任务配置将作业添加到调度器中。
        如果调度器中已存在该任务的旧作业，会先进行移除。

        :param task: 任务模型实例。
        """
        # 如果存在旧的调度作业，则先移除以避免重复执行
        if self.scheduler.get_job(str(task.id)):
            self.scheduler.remove_job(str(task.id))

        # 如果任务未激活，则不加入调度
        if not task.is_active:
            return

        trigger_args = task.schedule_config.copy()

        try:
            # 将任务加入 APScheduler
            self.scheduler.add_job(
                self.execute_task,
                trigger=task.schedule_type,  # 调度类型，如 cron, interval, date
                id=str(task.id),
                args=[task.id],
                replace_existing=True,
                **trigger_args
            )
            logger.info(f"Scheduled task {task.name} ({task.id}) with {task.schedule_type} {trigger_args}")
        except Exception as e:
            logger.error(f"Failed to schedule task {task.name}: {e}")

    async def create_task(self, task_data: Task) -> Task:
        """
        创建新的任务并加入调度。

        :param task_data: 任务模型实例。
        :return: 保存后的任务对象。
        """
        with Session(engine) as session:
            session.add(task_data)
            session.commit()
            session.refresh(task_data)
            self._schedule_job(task_data)
            return task_data

    async def update_task(self, task_id: UUID, update_data: Dict[str, Any]) -> Optional[Task]:
        """
        更新指定的任务配置并刷新其调度状态。

        :param task_id: 任务 ID。
        :param update_data: 包含更新字段的数据字典。
        :return: 更新后的任务对象，若不存在返回 None。
        """
        with Session(engine) as session:
            task = session.get(Task, task_id)
            if not task:
                return None

            # 动态应用属性更新
            for key, value in update_data.items():
                setattr(task, key, value)

            task.updated_at = datetime.now()
            session.add(task)
            session.commit()
            session.refresh(task)

            # 更新调度器中的作业
            self._schedule_job(task)
            return task

    async def delete_task(self, task_id: UUID) -> bool:
        """
        删除指定的任务，并从调度器中移除对应作业。

        :param task_id: 任务 ID。
        :return: 布尔值，表示是否成功删除。
        """
        with Session(engine) as session:
            task = session.get(Task, task_id)
            if not task:
                return False

            # 从调度器中移除
            if self.scheduler.get_job(str(task_id)):
                self.scheduler.remove_job(str(task_id))

            session.delete(task)
            session.commit()
            return True

    async def pause_task(self, task_id: UUID) -> Optional[Task]:
        """
        暂停任务，取消其激活状态并从调度中移除。

        :param task_id: 任务 ID。
        :return: 更新后的任务对象。
        """
        return await self.update_task(task_id, {"is_active": False})

    async def resume_task(self, task_id: UUID) -> Optional[Task]:
        """
        恢复任务，重新激活并加入调度。

        :param task_id: 任务 ID。
        :return: 更新后的任务对象。
        """
        return await self.update_task(task_id, {"is_active": True})

    async def execute_task(self, task_id: UUID):
        """
        执行指定任务的核心逻辑，并记录执行日志。
        支持执行系统脚本、Webhook、内置函数和 AI 对话等不同类型的任务。

        Session 生命周期: 读取阶段 → 关闭 session → 执行阶段（无 session） → 写入阶段（新 session）
        避免在长时间异步操作（子进程、HTTP、AI 流）期间持有数据库连接。

        :param task_id: 任务 ID。
        """
        logger.info(f"Executing task {task_id}")

        # ========== 读取阶段：短生命周期 session ==========
        with Session(engine) as session:
            task = session.get(Task, task_id)
            if not task:
                logger.error(f"Task {task_id} not found during execution")
                return

            # 创建初始日志条目，状态为 running
            log = TaskLog(task_id=task.id, status="running")
            session.add(log)
            session.commit()
            session.refresh(log)

            # 提取执行所需的纯值，避免在 session 关闭后访问 ORM 对象
            task_type = task.type
            task_payload = task.payload
            task_name = task.name
            log_id = log.id

        # ========== 执行阶段：不持有任何 session ==========
        start_time = datetime.now()
        output = ""
        status = "success"

        try:
            # ========== 根据任务类型分发执行逻辑 ==========
            if task_type == "script":
                # 执行 Shell 脚本类型任务
                proc = await asyncio.create_subprocess_shell(
                    task_payload,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                output = stdout.decode() + stderr.decode()
                # 根据返回码判断是否成功
                if proc.returncode != 0:
                    status = "failed"
                    output += f"\nExited with code {proc.returncode}"

            elif task_type == "webhook":
                # 执行 Webhook 请求任务
                async with httpx.AsyncClient() as client:
                    resp = await client.post(task_payload, timeout=30.0)
                    output = f"Status: {resp.status_code}\nResponse: {resp.text}"
                    if resp.status_code >= 400:
                        status = "failed"

            elif task_type == "function":
                # 执行内置的 Python 函数任务
                func = _FUNCTION_REGISTRY.get(task_payload)
                if func:
                    # 区分同步/异步函数进行调用
                    if asyncio.iscoroutinefunction(func):
                        await func()
                    else:
                        await asyncio.to_thread(func)
                    output = "Function executed successfully"
                else:
                    status = "failed"
                    output = f"Function {task_payload} not found in registry"

            elif task_type == "ai_dialogue":
                # 执行 AI 对话任务 (延迟导入避免循环依赖)
                from app.services.chat_service import chat_service as _chat_svc

                models = await _chat_svc.get_enabled_models()
                if not models:
                    status = "failed"
                    output = "No enabled AI models found."
                else:
                    model_id = models[0]["id"]
                    # 创建专属会话并立即关闭 session
                    with Session(engine) as s:
                        chat_sess = _chat_svc.create_session(s, title=f"Task: {task_name}")
                        chat_sess_id = chat_sess.id

                    # 收集流式输出（send_message 内部自管理 session）
                    chunks = []
                    with Session(engine) as s:
                        async for chunk in _chat_svc.send_message(s, chat_sess_id, task_payload, model_id):
                            chunks.append(chunk)

                    result = "".join(chunks)
                    status = "failed" if result.startswith("Error:") else "success"
                    output = result

            else:
                # 处理未知类型的异常情况
                status = "failed"
                output = f"Unknown task type: {task_type}"

        except Exception as e:
            # 捕获全局执行异常
            status = "failed"
            output = str(e)
            logger.error(f"Task execution failed: {e}")

        # ========== 写入阶段：新的短生命周期 session ==========
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() * 1000

        with Session(engine) as session:
            log = session.get(TaskLog, log_id)
            task = session.get(Task, task_id)

            if log:
                log.status = status
                log.output = output
                log.duration = duration
                session.add(log)

            if task:
                task.last_run_at = start_time
                session.add(task)

            session.commit()

# 全局任务服务单例
task_service = TaskService()
