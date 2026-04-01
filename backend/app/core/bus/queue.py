"""
异步消息队列模块
提供用于渠道与代理核心之间解耦通信的异步事件总线实现
"""

import asyncio

from app.core.bus.events import InboundMessage, OutboundMessage


class MessageBus:
    """
    异步消息总线类
    将聊天渠道（Channels）与代理核心（Agent Core）解耦。
    渠道将接收到的消息推入入站队列，代理由此消费并处理；
    代理将生成的回复推入出站队列，渠道由此消费并发送。
    """

    def __init__(self):
        """
        初始化消息总线实例，创建基于 asyncio 的入站和出站队列
        """
        # 入站队列：存储从各个渠道接收到的用户消息
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        # 出站队列：存储 AI 生成的准备发送到渠道的回复消息
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """
        发布一条从渠道接收到的入站消息到总线中，供 Agent 消费处理。
        
        :param msg: 封装好的入站消息对象
        :return: None
        """
        await self.inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """
        从总线中消费下一条入站消息。
        如果当前队列为空，则会挂起阻塞等待，直到有新消息到达。
        
        :return: 入站消息对象
        """
        return await self.inbound.get()

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """
        发布一条 Agent 生成的回复消息到出站队列中，供对应渠道消费发送。
        
        :param msg: 封装好的出站消息对象
        :return: None
        """
        await self.outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        """
        从总线中消费下一条出站消息。
        如果当前队列为空，则会挂起阻塞等待，直到有新消息到达。
        
        :return: 出站消息对象
        """
        return await self.outbound.get()

    @property
    def inbound_size(self) -> int:
        """
        获取当前积压在入站队列中待处理的消息数量。
        :return: 入站队列长度
        """
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        """
        获取当前积压在出站队列中待发送的消息数量。
        :return: 出站队列长度
        """
        return self.outbound.qsize()
