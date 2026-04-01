import logging
import os
from typing import Optional, Dict, Any, List
from sqlmodel import Session, select
from app.models.agent_store import AgentModel
from app.service_client.agents_sync_client import AgentsServiceSyncClient

# 初始化日志记录器
logger = logging.getLogger(__name__)

class AgentService:
    """
    Agent 服务类，负责处理与 Agent 相关的业务逻辑，如同步和获取图谱。
    采用单例模式设计，确保全局只实例化一个服务对象。
    """
    _instance = None

    def __new__(cls):
        """
        单例模式实例化方法。

        :return: AgentService 的单例对象。
        """
        # ========== 步骤1：检查实例是否存在 ==========
        if cls._instance is None:
            # 如果不存在，调用父类创建新实例
            cls._instance = super(AgentService, cls).__new__(cls)
            # 初始化同步客户端，用于与底层的 Agents Service 交互
            cls._instance.client = AgentsServiceSyncClient()
        return cls._instance

    async def sync_agents(self, session: Session):
        """
        同步 Agent 到数据库。
        从底层 Agents Service 获取所有可用的 Agent 列表，并更新或插入到本地数据库中。

        :param session: 数据库会话对象，用于执行数据库操作。
        """
        # 记录已同步的 Agent 列表
        synced_agents = []

        try:
            # ========== 步骤1：从外部服务获取 Agent 列表 ==========
            # 调用底层客户端获取最新的 Agent 信息
            agents_list = self.client.list_agents()

            # ========== 步骤2：遍历并同步到数据库 ==========
            for agent_info in agents_list:
                try:
                    # 尝试从数据库查询是否已存在同名的 Agent
                    db_agent = session.exec(select(AgentModel).where(AgentModel.name == agent_info.name)).first()

                    if db_agent:
                        # ========== 分支A：如果已存在，更新基本信息 ==========
                        db_agent.description = agent_info.description
                        db_agent.status = agent_info.status
                        # 此处为合并配置预留逻辑，当前未覆盖配置，以防丢失用户自定义设置
                        # db_agent.config = agent_info.config
                        session.add(db_agent)
                        synced_agents.append(db_agent)
                    else:
                        # ========== 分支B：如果不存在，创建新记录 ==========
                        new_agent = AgentModel(
                            name=agent_info.name,
                            description=agent_info.description,
                            type=agent_info.type,
                            status=agent_info.status,
                            config=agent_info.config
                        )
                        session.add(new_agent)
                        synced_agents.append(new_agent)
                except Exception as e:
                    # 捕获单个 Agent 同步时的异常，不中断整体流程
                    logger.error(f"Failed to sync agent {agent_info.name}: {e}")

            # ========== 步骤3：提交事务并刷新对象 ==========
            session.commit()
            for a in synced_agents:
                session.refresh(a)

        except Exception as e:
            # 捕获全局异常（如获取列表失败、整体数据库提交失败）
            logger.error(f"Failed to list agents from service: {e}")
            # 回滚事务以保持数据库数据的一致性
            session.rollback()

    async def get_graph_mermaid(self, agent_name: str) -> str:
        """
        获取 Agent 的 Mermaid 流程图代码。

        :param agent_name: 目标 Agent 的名称。
        :return: str 表示流程图的 Mermaid 语法字符串。
        """
        try:
            # 调用底层服务获取图表信息
            graph_contract = self.client.get_agent_graph(agent_name)
            # 返回提取出的 Mermaid 字符串
            return graph_contract.mermaid
        except Exception as e:
            # 异常处理：记录错误并返回一个包含错误信息的备用 Mermaid 图
            logger.error(f"Failed to get graph for {agent_name}: {e}")
            return f"graph TD;\n    Error[Failed to fetch graph: {str(e)}];"

# 实例化全局服务对象，供外部模块引用
agent_service = AgentService()
