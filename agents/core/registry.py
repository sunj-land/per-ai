"""
工具注册表 (Tool Registry)。
负责动态管理 Agent 可用的工具，包括注册、注销、查找和执行。
"""

from typing import Any, Dict, List, Optional
import logging

from tools.base import Tool

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    Agent 工具注册表类。

    提供工具的集中管理功能，允许在运行时动态添加或移除工具。
    Agent 通过此注册表来获取工具定义（Schema）并执行工具调用。
    """

    def __init__(self):
        """初始化空的工具注册表。"""
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """
        注册一个新工具。

        Args:
            tool (Tool): 要注册的工具实例。
        """
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """
        根据名称注销工具。

        Args:
            name (str): 要注销的工具名称。
        """
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[Tool]:
        """
        根据名称获取工具实例。

        Args:
            name (str): 工具名称。

        Returns:
            Optional[Tool]: 工具实例，如果未找到则返回 None。
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """
        检查指定名称的工具是否已注册。

        Args:
            name (str): 工具名称。

        Returns:
            bool: 如果已注册返回 True，否则返回 False。
        """
        return name in self._tools

    def get_definitions(self) -> List[Dict[str, Any]]:
        """
        获取所有已注册工具的定义（OpenAI Schema 格式）。
        通常用于在 Agent 初始化时告知 LLM 有哪些工具可用。

        Returns:
            List[Dict[str, Any]]: 工具定义列表。
        """
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, params: Dict[str, Any]) -> str:
        """
        执行指定工具。

        自动处理参数类型转换、验证和错误捕获。

        Args:
            name (str): 工具名称。
            params (Dict[str, Any]): 工具参数字典。

        Returns:
            str: 工具执行结果或错误信息。
        """
        _HINT = "\n\n[Analyze the error above and try a different approach.]"

        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found. Available: {', '.join(self.tool_names)}"

        try:
            # 1. 尝试根据 Schema 转换参数类型 (例如 string -> int)
            params = tool.cast_params(params)

            # 2. 验证参数是否符合 Schema
            errors = tool.validate_params(params)
            if errors:
                return f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors) + _HINT

            # 3. 执行工具
            result = await tool.execute(**params)

            # 4. 检查结果是否包含错误标识 (约定以 Error 开头)
            if isinstance(result, str) and result.startswith("Error"):
                return result + _HINT
            return result
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return f"Error executing {name}: {str(e)}" + _HINT

    @property
    def tool_names(self) -> List[str]:
        """
        获取所有已注册工具的名称列表。

        Returns:
            List[str]: 工具名称列表。
        """
        return list(self._tools.keys())

    def __len__(self) -> int:
        """返回已注册工具的数量。"""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """支持 'name in registry' 语法检查工具是否存在。"""
        return name in self._tools
