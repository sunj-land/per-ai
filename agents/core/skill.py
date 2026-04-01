from abc import ABC, abstractmethod
from typing import Any, Dict

class Skill(ABC):
    """
    所有技能的基类 (Base class for all skills)。
    技能是 Agent 可以使用的模块化能力，封装了特定的功能逻辑。
    """
    
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any], output_schema: Dict[str, Any]):
        """
        初始化技能实例。

        Args:
            name (str): 技能名称，用于标识技能。
            description (str): 技能的详细描述，Agent 可据此理解技能用途。
            input_schema (Dict[str, Any]): 输入数据的 Schema 定义，用于验证输入。
            output_schema (Dict[str, Any]): 输出数据的 Schema 定义，用于描述输出结构。
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.is_loaded = False

    @abstractmethod
    def execute(self, inputs: Any, **kwargs) -> Any:
        """
        执行技能的核心逻辑。
        子类必须实现此方法以提供具体的技能行为。

        Args:
            inputs (Any): 技能所需的输入数据，应符合 input_schema。
            **kwargs: 其他可选参数，提供额外的执行上下文。

        Returns:
            Any: 技能执行的结果，应符合 output_schema。
        """
        pass

    def load(self):
        """
        加载技能所需的必要资源（如模型权重、配置文件、数据库连接等）。
        默认实现仅将 is_loaded 标记为 True。子类可重写此方法以执行具体的加载逻辑。
        """
        self.is_loaded = True

    def unload(self):
        """
        释放技能占用的资源。
        默认实现仅将 is_loaded 标记为 False。子类可重写此方法以执行具体的清理逻辑。
        """
        self.is_loaded = False
