import re
import shlex
import logging
import asyncio
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ShellRiskEngine:
    """
    多维度 Shell 指令风险评估引擎。
    包含命令白名单、敏感操作检测、路径权限检查、危险参数识别等规则。
    """

    def __init__(
        self,
        custom_whitelist: Optional[List[str]] = None,
        custom_blacklist: Optional[List[str]] = None,
        custom_sensitive_paths: Optional[List[str]] = None,
        custom_dangerous_patterns: Optional[List[str]] = None
    ):
        """
        初始化风控引擎。
        :param custom_whitelist: 自定义命令白名单列表
        :param custom_blacklist: 自定义敏感命令黑名单列表
        :param custom_sensitive_paths: 自定义敏感路径列表
        :param custom_dangerous_patterns: 自定义危险参数正则表达式列表
        """
        # 默认白名单命令
        self.whitelist = custom_whitelist if custom_whitelist is not None else ["ls", "pwd", "echo", "cat", "grep", "whoami", "date", "cd", "head", "tail", "wc", "awk", "sed"]

        # 敏感命令黑名单 (高危)
        self.blacklist_commands = custom_blacklist if custom_blacklist is not None else ["rm", "mv", "chmod", "chown", "kill", "reboot", "shutdown", "mkfs", "dd", "wget", "curl", "nc", "bash", "sh", "zsh"]

        # 敏感路径 (高危)
        self.sensitive_paths = custom_sensitive_paths if custom_sensitive_paths is not None else ["/etc", "/bin", "/usr/bin", "/root", "/var/run", "/boot", "/dev", "/sys", "/proc"]

        # 危险参数正则表达式
        self.dangerous_patterns = custom_dangerous_patterns if custom_dangerous_patterns is not None else [
            r"rm\s+-r",           # 递归删除
            r"rm\s+-f",           # 强制删除
            r">\s*/dev/sda",      # 覆盖磁盘
            r"chmod\s+777",       # 权限全开
            r">\s*/etc/",         # 覆盖配置
            r"\|.*bash",          # 管道执行bash
            r"&\s*/dev/tcp"       # 反弹shell
        ]

    def assess(self, command: str, config_override: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        对给定的 shell 命令进行多维度风险评估。
        :param command: 待评估的 shell 命令字符串
        :param config_override: 动态风控规则配置覆盖，支持覆盖 whitelist, blacklist_commands, sensitive_paths, dangerous_patterns
        :return: 包含评估结果、风险级别和风险详情的字典
        """
        risk_level = "LOW"
        is_safe = True
        risk_details = []

        # 应用动态配置覆盖
        config_override = config_override or {}
        current_whitelist = config_override.get("whitelist", self.whitelist)
        current_blacklist = config_override.get("blacklist_commands", self.blacklist_commands)
        current_sensitive_paths = config_override.get("sensitive_paths", self.sensitive_paths)
        current_dangerous_patterns = config_override.get("dangerous_patterns", self.dangerous_patterns)

        if not command or not command.strip():
            return {"is_safe": False, "risk_level": "LOW", "risk_details": ["空命令"]}

        # ========== 步骤1：危险参数正则匹配（高危） ==========
        for pattern in current_dangerous_patterns:
            if re.search(pattern, command):
                is_safe = False
                risk_level = "HIGH"
                risk_details.append(f"匹配到危险参数模式: {pattern}")

        # ========== 步骤2：解析命令词法 ==========
        try:
            tokens = shlex.split(command)
        except ValueError as e:
            # 引号未闭合等语法错误，无法准确分析
            return {"is_safe": False, "risk_level": "HIGH", "risk_details": [f"命令解析失败: {str(e)}"]}

        if not tokens:
            return {"is_safe": False, "risk_level": "LOW", "risk_details": ["无法提取有效命令部分"]}

        base_cmd = tokens[0]

        # ========== 步骤3：敏感操作检测（黑名单，高危） ==========
        if base_cmd in current_blacklist:
            is_safe = False
            risk_level = "HIGH"
            risk_details.append(f"使用了黑名单高危命令: {base_cmd}")

        # ========== 步骤4：命令白名单检测（中危） ==========
        elif base_cmd not in current_whitelist:
            is_safe = False
            if risk_level != "HIGH":
                risk_level = "MEDIUM"
            risk_details.append(f"命令不在白名单内: {base_cmd}")

        # ========== 步骤5：路径权限检查（高危） ==========
        for token in tokens[1:]:
            for spath in current_sensitive_paths:
                if token.startswith(spath):
                    is_safe = False
                    risk_level = "HIGH"
                    risk_details.append(f"访问或操作了敏感路径: {spath}")
                    break

        # ========== 步骤6：日志记录与返回 ==========
        if not is_safe:
            logger.warning(f"风控拦截 | 级别: {risk_level} | 命令: {command} | 原因: {', '.join(risk_details)}")
        else:
            logger.info(f"风控放行 | 级别: {risk_level} | 命令: {command}")

        return {
            "is_safe": is_safe,
            "risk_level": risk_level,
            "risk_details": risk_details
        }

class ShellExecutionTool:
    """
    安全的 Shell 命令执行工具。
    """

    async def execute(self, command: str) -> Dict[str, Any]:
        """
        异步执行 Shell 命令并返回结果。
        :param command: 要执行的命令字符串
        :return: 包含标准输出、标准错误和退出码的字典
        """
        # ========== 步骤1：创建异步子进程 ==========
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # ========== 步骤2：等待进程完成并获取输出 ==========
        stdout, stderr = await process.communicate()

        # ========== 步骤3：返回执行结果 ==========
        return {
            "stdout": stdout.decode("utf-8").strip() if stdout else "",
            "stderr": stderr.decode("utf-8").strip() if stderr else "",
            "returncode": process.returncode
        }
