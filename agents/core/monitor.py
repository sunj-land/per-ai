import os
import json
import time
import logging

logger = logging.getLogger(__name__)

# 指标日志文件目录
# 从环境变量 AGENT_METRICS_DIR 获取，如果未设置则默认为当前文件所在目录的上两级目录下的 logs 文件夹
LOG_DIR = os.getenv(
    "AGENT_METRICS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../logs")),
)
METRICS_FILE = os.path.join(LOG_DIR, "agent_metrics.jsonl")

# 确保日志目录存在，如果不存在则创建
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

class AgentMonitor:
    """
    Agent 监控类，负责记录和读取 Agent 的运行指标。
    主要用于跟踪 Agent 的请求处理延迟、状态、意图类型以及错误信息。
    数据以 JSONL (JSON Lines) 格式存储，方便追加写入和逐行读取。
    """

    @staticmethod
    def log_request(agent_name: str, intent: str, latency: float, status: str, error: str = None):
        """
        记录一次 Agent 请求的详细指标到日志文件中。
        此方法将请求的关键信息封装为字典，并追加写入到 METRICS_FILE 中。

        Args:
            agent_name (str): 处理请求的 Agent 名称 (如 "master", "article")。
            intent (str): 识别到的用户意图类型 (如 "search_articles", "general_chat")。
            latency (float): 请求处理耗时，单位为毫秒 (ms)。
            status (str): 处理状态 (如 "success", "error")。
            error (str, optional): 如果状态为 error，记录具体的错误信息；否则为 None。
        """
        # 构建指标数据条目
        entry = {
            "timestamp": time.time(), # 记录当前时间戳
            "agent": agent_name,      # Agent 标识
            "intent": intent,         # 意图分类
            "latency_ms": latency,    # 性能指标
            "status": status,         # 执行结果
            "error": error            # 错误详情（如有）
        }

        try:
            # 以追加模式 ('a') 打开文件，确保不覆盖现有日志
            with open(METRICS_FILE, "a", encoding="utf-8") as f:
                # 将字典转换为 JSON 字符串并写入一行
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # 记录日志写入失败的错误，避免监控逻辑影响主流程
            logger.error(f"Failed to write metrics: {e}")

    @staticmethod
    def get_recent_metrics(limit: int = 100) -> list:
        """
        读取最近的指标数据，通常用于监控仪表盘显示或健康检查。
        此方法读取日志文件的最后 N 行，并将其解析为字典列表。

        Args:
            limit (int): 需要返回的最大记录数，默认为 100 条。

        Returns:
            list: 包含指标字典的列表。如果文件不存在或读取失败，返回空列表。
        """
        metrics = []
        # 检查指标文件是否存在，如果不存在直接返回空列表
        if not os.path.exists(METRICS_FILE):
            return metrics

        try:
            # 以只读模式 ('r') 打开文件
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 仅处理最后 limit 行数据，实现“最近记录”的逻辑
                # 使用切片 [-limit:] 获取列表末尾的元素
                for line in lines[-limit:]:
                    try:
                        # 解析每一行 JSON 数据
                        metrics.append(json.loads(line))
                    except json.JSONDecodeError:
                        # 忽略格式错误的行（可能是写入中断导致的残缺行）
                        continue
        except Exception as e:
            # 捕获读取过程中的任何错误（如文件权限问题）
            logger.error(f"Failed to read metrics: {e}")

        return metrics
