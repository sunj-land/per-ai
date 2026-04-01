import asyncio
import logging
from app.core.bus import bus
from app.core.bus.events import OutboundMessage

logger = logging.getLogger(__name__)

class OutboundDispatcher:
    """
    出站消息分发器
    负责从事件总线（Bus）的 Outbound 队列中消费消息，
    并根据消息的目标渠道（如 web、qqbot 等）将消息路由到对应的处理逻辑。
    """
    def __init__(self):
        """
        初始化分发器实例，设置运行状态和后台任务对象。
        """
        # 运行状态标识
        self._running = False
        # 异步循环任务实例
        self._task = None

    def start(self):
        """
        启动分发器的事件循环任务。
        如果当前未运行，则创建并启动异步后台任务进行持续监听。
        :return: None
        """
        if not self._running:
            self._running = True
            # 创建并启动后台监听协程
            self._task = asyncio.create_task(self._loop())

    def stop(self):
        """
        停止分发器。
        修改运行状态标识，并尝试取消后台正在运行的任务。
        :return: None
        """
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        """
        核心事件监听循环。
        持续从总线消费出站消息，并为每条消息创建独立的异步分发任务，
        避免阻塞主循环的执行。
        :return: None
        """
        logger.info("OutboundDispatcher started")
        while self._running:
            try:
                # ========== 步骤1：从总线异步获取一条出站消息 ==========
                msg = await bus.consume_outbound()

                # ========== 步骤2：创建独立协程执行消息的分发逻辑 ==========
                asyncio.create_task(self._dispatch_message(msg))
            except asyncio.CancelledError:
                # 捕获任务取消异常，安全退出循环
                break
            except Exception as e:
                # 记录其他异常，防止循环崩溃
                logger.error(f"Error in OutboundDispatcher: {e}")

    async def _dispatch_message(self, msg: OutboundMessage):
        """
        分发单条消息到对应的具体渠道。
        :param msg: 需要被分发的出站消息对象
        :return: None
        """
        logger.info(f"Dispatching outbound message to {msg.channel}:{msg.chat_id}")
        try:
            # ========== 步骤3：根据渠道类型进行路由 ==========
            if msg.channel == "web":
                # 渠道为 web 时，将消息块直接放入元数据中绑定的响应队列，供 SSE 流式返回
                queue = msg.metadata.get("response_queue")
                if queue:
                    progress = msg.metadata.get("progress", False)
                    if progress:
                        # 流式生成中的数据块，直接推入队列
                        await queue.put(msg.content)
                    else:
                        # 流式生成结束信号，推入 None
                        await queue.put(None)

            elif msg.channel == "qqbot":
                # 渠道为 qqbot 时，通过 channel_service 发送文本消息到对应外部平台
                # 延迟导入以避免循环依赖问题
                from app.services.channel_service import channel_service
                import uuid

                content = msg.content
                channel_id_str = msg.metadata.get("channel_id")

                if content and channel_id_str:
                    try:
                        # 确保 channel_id 为合法的 UUID 格式
                        channel_id = uuid.UUID(str(channel_id_str))
                        # 调用 channel_service 将最终消息推送到 QQ 机器人平台
                        await channel_service.send_message(
                            channel_id=channel_id,
                            content=content
                        )
                    except ValueError:
                        logger.error(f"Invalid channel_id format: {channel_id_str}")
                else:
                    logger.warning(f"Cannot dispatch qqbot message: missing content or channel_id. channel_id={channel_id_str}")

        except Exception as e:
            # ========== 步骤4：异常捕获 ==========
            logger.error(f"Failed to dispatch message: {e}")

# 全局单例的分发器实例
outbound_dispatcher = OutboundDispatcher()
