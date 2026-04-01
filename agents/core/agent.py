"""
模块职责: 本文件定义了 Agent 的抽象基类与生命周期状态，为所有具体 Agent 提供统一的行为契约和技能管理能力。
输入输出: 核心输入为字典格式的任务数据 `task: Dict[str, Any]`，输出为处理结果字典 `Dict[str, Any]`。
关键算法: 基于模板方法模式（Template Method），抽象出 `process_task` 供子类实现，在 `execute` 方法中统一管控状态与异常。
异常处理: 在 `execute` 方法内捕获顶层异常，记录到 memory 中，并将 Agent 状态置为 ERROR，防止未捕获异常导致服务崩溃。
并发安全: 当前基于 asyncio 协程运行，若多个任务并发调用同一个 Agent 实例的 `execute`，会导致 `self.status` 出现资源竞争（无锁保护），在多线程/高并发场景下需引入 `asyncio.Lock`。
性能瓶颈: `self.memory` 是无界列表，长期运行且任务频繁时可能导致内存泄漏，建议引入容量限制或 LRU 淘汰机制。
外部依赖: `uuid` (生成ID), `logging` (日志记录), `agents.core.skill.Skill` (技能定义), `skills.registry.SkillRegistry` (技能注册表)。
配置项说明:
- config: 初始化时传入的配置字典，通常包含大模型参数、特定的业务阈值等。

维护者: SunJie
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import uuid
from enum import Enum
import logging
from core.skill import Skill
from skills.registry import SkillRegistry

# 实例化当前模块日志记录器
logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """
    Agent 状态枚举
    定义 Agent 在生命周期中的不同状态
    """
    # 空闲状态，准备接收任务
    IDLE = "idle"       
    # 忙碌状态，正在处理任务
    BUSY = "busy"       
    # 错误状态，任务执行发生异常失败
    ERROR = "error"     
    # 停止状态，Agent 已停止工作，拒绝新任务
    STOPPED = "stopped" 

class Agent(ABC):
    """
    Agent 抽象基类
    所有具体业务 Agent 实现的父类，提供生命周期管理、状态流转及技能加载的默认实现。
    """

    def __init__(self, name: str, description: str, config: Dict[str, Any] = None):
        """
        初始化 Agent 实例。

        :param name: Agent 的名称，用于唯一标识和日志追踪。
        :param description: Agent 的描述，说明其特定功能和用途。
        :param config: Agent 的配置信息字典，如模型参数、API 密钥等。默认为空字典。
        """
        # 生成唯一的 Agent ID 标识
        self.id = str(uuid.uuid4()) 
        # Agent 业务名称
        self.name = name
        # Agent 功能描述
        self.description = description
        # 兜底配置为空字典
        self.config = config or {}
        # 存储 Agent 拥有的技能，key 为技能名称
        self.skills: Dict[str, Skill] = {} 
        # 初始状态默认流转为 IDLE
        self.status = AgentStatus.IDLE   
        # 简单的内存日志，记录任务执行历史，注意: 当前无容量限制
        self.memory: List[Dict[str, Any]] = [] 

    def register_skill(self, skill: Skill):
        """
        为 Agent 注册并绑定一个具体技能。

        :param skill: 要注册的技能实例对象。
        """
        self.skills[skill.name] = skill
        logger.info(f"Agent {self.name} registered skill: {skill.name}") 

    def load_skill(self, skill_name: str):
        """
        通过技能名称从全局技能注册表 (SkillRegistry) 中加载并绑定技能。

        :param skill_name: 要动态加载的技能名称标识。
        """
        skill_instance = SkillRegistry.get_skill_instance(skill_name)
        if skill_instance:
            self.register_skill(skill_instance)
        else:
            logger.error(f"Skill {skill_name} not found in registry.") 

    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理任务的核心业务逻辑 (抽象方法)。
        必须由具体的 Agent 子类实现以提供真实处理能力。

        :param task: 任务数据字典。
        :return: 任务处理结果字典。
        """
        pass

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务并处理生命周期/状态管理。
        外部调用 Agent 执行任务的唯一标准入口，使用模板方法模式包裹具体业务逻辑。

        :param task: 任务数据字典。
        :return: 执行结果，包含最终状态和数据。
        """
        # ========== 步骤1：拦截非活动状态 ==========
        if self.status == AgentStatus.STOPPED:
            return {"status": "error", "message": "Agent is stopped"}

        # ========== 步骤2：流转为处理状态 ==========
        # 注意: 此处在并发环境下存在条件竞争风险
        self.status = AgentStatus.BUSY 
        
        try:
            logger.info(f"Agent {self.name} starting task: {task}")
            # ========== 步骤3：执行核心业务逻辑 ==========
            result = await self.process_task(task)
            
            # ========== 步骤4：记录执行成功历史 ==========
            self.memory.append({"task": task, "result": result, "status": "success"})
            return result
        except Exception as e:
            # ========== 异常处理：捕获执行错误并变更状态 ==========
            logger.error(f"Agent {self.name} failed task: {e}")
            self.status = AgentStatus.ERROR 
            self.memory.append({"task": task, "error": str(e), "status": "failed"})
            return {"status": "error", "message": str(e)}
        finally:
            # ========== 步骤5：恢复状态（如果未出错） ==========
            if self.status != AgentStatus.ERROR:
                self.status = AgentStatus.IDLE

    def start(self):
        """
        启动 Agent
        将其状态重置为 IDLE，允许接收新任务。
        """
        self.status = AgentStatus.IDLE
        logger.info(f"Agent {self.name} started.")

    def stop(self):
        """
        停止 Agent
        将其状态设置为 STOPPED，拒绝新任务的执行。
        """
        self.status = AgentStatus.STOPPED
        logger.info(f"Agent {self.name} stopped.")

    def get_status(self) -> Dict[str, Any]:
        """
        获取 Agent 的当前运行时状态信息。

        :return: 包含 ID、名称、状态值和已注册技能列表的字典。
        """
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "skills": list(self.skills.keys())
        }
