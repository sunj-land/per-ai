from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time

class BaseAdapter(ABC):
    """
    所有渠道适配器的抽象基类。
    定义了渠道必须实现的发送、接收和验证接口，
    并内置了健康状态与性能指标（Metrics）统计功能。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化渠道适配器
        :param config: 渠道特有配置字典（如 webhook_url, app_id 等）
        """
        # 渠道特有配置参数
        self.config = config
        # 当前适配器绑定的渠道全局唯一 ID
        self.channel_id = None
        # 内部性能统计字典
        self._metrics = {
            "send_total": 0,       # 发送总数
            "send_success": 0,     # 发送成功数
            "send_failure": 0,     # 发送失败数
            "total_latency_ms": 0.0, # 总延迟（毫秒）
        }

    def set_channel_id(self, channel_id: str):
        """
        设置当前适配器绑定的渠道唯一 ID
        :param channel_id: 渠道 ID 字符串
        :return: None
        """
        self.channel_id = channel_id

    @abstractmethod
    async def send_text(self, content: str) -> Dict[str, Any]:
        """
        发送纯文本消息（由子类实现）
        :param content: 要发送的文本内容
        :return: 包含发送状态的字典
        """
        pass

    @abstractmethod
    async def send_markdown(self, title: str, content: str) -> Dict[str, Any]:
        """
        发送 Markdown 格式消息（由子类实现）
        :param title: 消息标题
        :param content: Markdown 格式的内容
        :return: 包含发送状态的字典
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证适配器配置是否合法完整（由子类实现）
        :return: 配置合法返回 True，否则返回 False
        """
        pass

    async def authenticate(self) -> bool:
        """
        与渠道提供商进行认证（可选实现）
        :return: 认证成功返回 True
        """
        return True

    async def receive(self, payload: Dict[str, Any]) -> Any:
        """
        处理传入的 Webhook 请求（由子类实现）
        :param payload: Webhook 请求体数据
        :return: 处理结果或标准回复格式
        :raises NotImplementedError: 如果子类不支持 Webhook 则抛出异常
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support webhook receive yet.")

    def record_metric(self, success: bool, latency_ms: float) -> None:
        """
        记录单次发送操作的性能指标
        :param success: 发送是否成功
        :param latency_ms: 发送耗时（毫秒）
        :return: None
        """
        # ========== 步骤1：更新总发送计数 ==========
        self._metrics["send_total"] += 1

        # ========== 步骤2：更新成功/失败计数 ==========
        if success:
            self._metrics["send_success"] += 1
        else:
            self._metrics["send_failure"] += 1

        # ========== 步骤3：累加耗时 ==========
        self._metrics["total_latency_ms"] += latency_ms

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取当前渠道适配器的综合性能指标
        :return: 包含总数、成功数、失败数、成功率及平均延迟的字典
        """
        total = self._metrics["send_total"]
        # ========== 步骤1：计算成功率（避免除零） ==========
        success_rate = self._metrics["send_success"] / total if total > 0 else 1.0

        # ========== 步骤2：计算平均延迟 ==========
        avg_latency = self._metrics["total_latency_ms"] / total if total > 0 else 0.0

        return {
            "send_total": total,
            "send_success": self._metrics["send_success"],
            "send_failure": self._metrics["send_failure"],
            "success_rate": round(success_rate, 4),
            "average_latency_ms": round(avg_latency, 2)
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        获取健康状态检查结果
        :return: 包含运行状态与指标数据的字典
        """
        return {
            "status": "ok",
            "metrics": self.get_metrics()
        }
