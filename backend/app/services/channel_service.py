from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
from sqlmodel import Session, select, func
from app.models.channel import Channel, ChannelMessage, ChannelCreate, ChannelUpdate
from app.core.channel.factory import AdapterFactory
from app.core.database import engine
from app.core.html_utils import html_to_markdown
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

class ChannelService:
    """
    渠道服务类，负责管理渠道 (Channel) 及其消息的创建、查询、更新、删除和发送逻辑。
    提供统一的消息发送路由及错误重试机制。
    """
    def create_channel(self, channel: ChannelCreate) -> Channel:
        """
        创建新的消息渠道。

        :param channel: 包含渠道创建信息的 Pydantic 模型。
        :return: 新创建并持久化到数据库的渠道对象。
        """
        with Session(engine) as session:
            db_channel = Channel.model_validate(channel)
            session.add(db_channel)
            session.commit()
            session.refresh(db_channel)
            return db_channel

    def get_channels(self, skip: int = 0, limit: int = 100) -> List[Channel]:
        """
        分页获取渠道列表。

        :param skip: 分页跳过的记录数。
        :param limit: 每页返回的最大记录数。
        :return: 渠道对象列表。
        """
        with Session(engine) as session:
            return session.exec(select(Channel).offset(skip).limit(limit)).all()

    def get_channel(self, channel_id: UUID) -> Optional[Channel]:
        """
        根据 ID 获取指定的渠道。

        :param channel_id: 渠道的唯一标识 (UUID)。
        :return: 找到的渠道对象，若不存在则返回 None。
        """
        with Session(engine) as session:
            return session.get(Channel, channel_id)

    def update_channel(self, channel_id: UUID, channel: ChannelUpdate) -> Optional[Channel]:
        """
        更新指定的渠道信息。

        :param channel_id: 要更新的渠道 ID。
        :param channel: 包含需更新字段的 Pydantic 模型。
        :return: 更新后的渠道对象，如果渠道不存在则返回 None。
        """
        with Session(engine) as session:
            db_channel = session.get(Channel, channel_id)
            if not db_channel:
                return None

            channel_data = channel.model_dump(exclude_unset=True)
            for key, value in channel_data.items():
                setattr(db_channel, key, value)

            session.add(db_channel)
            session.commit()
            session.refresh(db_channel)
            return db_channel

    def delete_channel(self, channel_id: UUID) -> bool:
        """
        删除指定的渠道。

        :param channel_id: 要删除的渠道 ID。
        :return: 删除成功返回 True，如果渠道不存在则返回 False。
        """
        with Session(engine) as session:
            channel = session.get(Channel, channel_id)
            if not channel:
                return False
            session.delete(channel)
            session.commit()
            return True

    def get_channel_messages(self, channel_id: UUID, skip: int = 0, limit: int = 100) -> List[ChannelMessage]:
        """
        获取指定 Channel 的消息历史
        :param channel_id: Channel ID
        :param skip: 跳过条数
        :param limit: 限制条数
        :return: 消息列表
        """
        with Session(engine) as session:
            # ========== 步骤1：查询数据库 ==========
            # 根据 channel_id 筛选消息，按创建时间倒序排列
            statement = select(ChannelMessage).where(ChannelMessage.channel_id == channel_id).order_by(ChannelMessage.created_at.desc()).offset(skip).limit(limit)
            return session.exec(statement).all()

    def get_messages(
        self,
        skip: int = 0,
        limit: int = 100,
        channel_id: Optional[UUID] = None,
        keyword: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取消息列表，支持多维度过滤
        :param skip: 跳过条数
        :param limit: 限制条数
        :param channel_id: Channel ID (可选)
        :param keyword: 关键词 (可选)
        :param start_date: 开始时间 (可选)
        :param end_date: 结束时间 (可选)
        :param status: 状态 (可选)
        :return: {items: List[ChannelMessage], total: int}
        """
        with Session(engine) as session:
            # ========== 步骤1：构建查询语句 ==========
            statement = select(ChannelMessage)

            if channel_id:
                statement = statement.where(ChannelMessage.channel_id == channel_id)
            if keyword:
                statement = statement.where(ChannelMessage.content.contains(keyword))
            if start_date:
                statement = statement.where(ChannelMessage.created_at >= start_date)
            if end_date:
                statement = statement.where(ChannelMessage.created_at <= end_date)
            if status:
                statement = statement.where(ChannelMessage.status == status)

            # ========== 步骤2：获取总数 ==========
            # 使用 func.count() 获取符合条件的总数
            count_statement = select(func.count()).select_from(statement.subquery())
            total = session.exec(count_statement).one()

            # ========== 步骤3：分页查询 ==========
            statement = statement.order_by(ChannelMessage.created_at.desc()).offset(skip).limit(limit)
            items = session.exec(statement).all()

            return {"items": items, "total": total}


    async def send_message(self, channel_id: UUID, content: str, title: Optional[str] = None) -> ChannelMessage:
        """
        向指定渠道发送消息，并记录发送状态。
        支持 HTML 到 Markdown 的自动转换，以及基于渠道配置的重试和回退路由策略。

        :param channel_id: 渠道 ID。
        :param content: 消息内容（支持文本、HTML、Markdown）。
        :param title: 消息标题（可选）。
        :return: 保存发送结果的 ChannelMessage 对象。
        :raises ValueError: 渠道不存在、未激活或认证失败时抛出。
        """
        # ========== 步骤1：内容预处理 ==========
        # 检查内容是否包含 HTML 标签，如果是则转换为 Markdown，防止下游解析错误
        if bool(re.search(r'<(div|p|img|br|span|figure|a|strong|b|i|em)\b[^>]*>', content, re.IGNORECASE)):
            logger.info("Detected HTML content in send_message, converting to Markdown...")
            content = html_to_markdown(content)

        # ========== 步骤2：检查渠道状态并创建初始消息记录 ==========
        with Session(engine) as session:
            channel = session.get(Channel, channel_id)
            if not channel:
                raise ValueError("Channel not found")

            if not channel.is_active:
                raise ValueError("Channel is inactive")

            # 解析渠道的路由和重试策略
            channel_config = dict(channel.config) if channel.config else {}
            routing_rules = channel_config.get("routing_rules", [])
            max_retries = channel_config.get("max_retries", 3)

            # 如果路由规则指定了回退序列，则使用它；否则默认使用当前渠道类型
            target_types = routing_rules if routing_rules else [channel.type]

            # 插入“等待发送”状态的消息记录
            message = ChannelMessage(
                channel_id=channel_id,
                content=content,
                status="pending"
            )
            session.add(message)
            session.commit()
            session.refresh(message)

            message_id = message.id

        status = "failed"
        result_str = ""
        last_exception = None

        # ========== 步骤3：尝试通过不同路由类型发送消息 ==========
        for target_type in target_types:
            try:
                # 获取适配器实例并检查认证状态
                adapter = AdapterFactory.get_adapter(target_type, channel_config)
                auth_success = await adapter.authenticate()
                if not auth_success:
                    raise ValueError(f"Authentication failed for {target_type}")

                retry_count = 0
                while retry_count < max_retries:
                    try:
                        # 根据是否提供标题决定发送 Markdown 还是纯文本
                        if title:
                            result = await adapter.send_markdown(title, content)
                        else:
                            result = await adapter.send_text(content)

                        status = "success"
                        result_str = json.dumps(result)
                        logger.info(f"Successfully sent message to channel {channel_id} via {target_type} on attempt {retry_count + 1}")
                        break
                    except Exception as e:
                        retry_count += 1
                        last_exception = e
                        logger.warning(f"Failed to send message via {target_type} (Attempt {retry_count}/{max_retries}): {e}")
                        # 指数退避延迟重试
                        if retry_count < max_retries:
                            await asyncio.sleep(0.5 * retry_count)

                # 若当前路由类型发送成功，则不再尝试备用路由
                if status == "success":
                    break
            except Exception as e:
                logger.error(f"Error configuring/authenticating adapter {target_type}: {e}")
                last_exception = e

        # ========== 步骤4：处理最终失败情况并更新消息状态 ==========
        if status == "failed":
            result_str = str(last_exception)
            logger.error(f"Final failure sending message to channel {channel_id} after trying all routes.", exc_info=True)

        with Session(engine) as session:
            message = session.get(ChannelMessage, message_id)
            if message:
                message.status = status
                message.result = result_str
                session.add(message)
                session.commit()
                session.refresh(message)
            return message

    async def handle_webhook(self, channel_id: UUID, payload: Dict[str, Any]) -> Any:
        """
        统一的 Webhook / REST 入口。
        将传入的 Webhook 载荷路由到相应渠道的接收方法。

        :param channel_id: 渠道 ID。
        :param payload: Webhook 请求携带的 JSON 数据。
        :return: 处理结果。
        """
        with Session(engine) as session:
            channel = session.get(Channel, channel_id)
            if not channel:
                return {"status": "error", "reason": f"Channel {channel_id} not found"}
            if not channel.is_active:
                return {"status": "error", "reason": f"Channel {channel_id} is inactive"}

            try:
                adapter = AdapterFactory.get_adapter(channel.type, channel.config)
                # Pass channel_id to adapter if it has a way to store it
                if hasattr(adapter, 'set_channel_id'):
                    adapter.set_channel_id(str(channel_id))
                return await adapter.receive(payload)
            except NotImplementedError:
                return {"status": "error", "reason": f"Channel {channel.type} does not support webhooks"}
            except Exception as e:
                logger.error(f"Error handling webhook for channel {channel_id}: {e}")
                return {"status": "error", "reason": "Internal error processing webhook"}

    def get_health_metrics(self) -> Dict[str, Any]:
        """
        获取所有激活渠道的综合健康状况和指标。
        （在实际应用中通常维护有状态的适配器，此处则通过查询数据库并验证配置实现）

        :return: 包含各渠道健康状态的字典。
        """
        health_status = {}
        with Session(engine) as session:
            channels = session.exec(select(Channel).where(Channel.is_active == True)).all()
            for channel in channels:
                try:
                    adapter = AdapterFactory.get_adapter(channel.type, channel.config)
                    is_valid = adapter.validate_config()
                    health_status[str(channel.id)] = {
                        "name": channel.name,
                        "type": channel.type,
                        "status": "ok" if is_valid else "invalid_config"
                    }
                except Exception as e:
                    health_status[str(channel.id)] = {"status": "error", "reason": str(e)}
        return health_status

    async def broadcast(self, content: str, title: Optional[str] = None) -> List[ChannelMessage]:
        """
        向所有激活状态的渠道广播消息。

        :param content: 广播的消息内容。
        :param title: 消息标题（可选）。
        :return: 发送成功的 ChannelMessage 列表。
        """
        with Session(engine) as session:
            channels = session.exec(select(Channel).where(Channel.is_active == True)).all()
            channel_ids = [c.id for c in channels]

        results = []
        for channel_id in channel_ids:
            try:
                msg = await self.send_message(channel_id, content, title)
                results.append(msg)
            except Exception as e:
                # 记录错误但不中断广播
                print(f"Failed to send to channel {channel_id}: {e}")
        return results

channel_service = ChannelService()
