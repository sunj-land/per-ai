"""
Agent 工具基类 (Base Class for Agent Tools)。
定义了所有工具必须遵循的接口和通用行为，包括参数验证、类型转换等。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

class Tool(ABC):
    """
    Agent 工具的抽象基类。

    工具是 Agent 与环境交互的能力封装，例如读取文件、执行命令、搜索网络等。
    每个具体的工具都必须继承此类并实现必要的属性和方法。
    """

    # 类型映射表，用于参数类型转换和验证
    _TYPE_MAP = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    @property
    @abstractmethod
    def name(self) -> str:
        """
        工具名称。
        Agent 在调用工具时使用的唯一标识符。
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        工具描述。
        详细说明工具的功能、用途和副作用，帮助 Agent 理解何时以及如何使用此工具。
        """
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        工具参数的 JSON Schema 定义。
        用于描述工具接受的参数结构、类型和约束条件。
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """
        执行工具逻辑。

        Args:
            **kwargs: 工具特定的参数，应符合 parameters 定义的 Schema。

        Returns:
            str: 工具执行的结果字符串。
        """
        pass

    def cast_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        在验证之前，根据 Schema 对参数进行安全的类型转换。
        例如，将字符串 "123" 转换为整数 123（如果 Schema 要求整数）。

        Args:
            params (Dict[str, Any]): 原始参数字典。

        Returns:
            Dict[str, Any]: 转换后的参数字典。
        """
        schema = self.parameters or {}
        if schema.get("type", "object") != "object":
            return params

        return self._cast_object(params, schema)

    def _cast_object(self, obj: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
        """根据 Schema 转换对象（字典）中的值。"""
        if not isinstance(obj, dict):
            return obj

        props = schema.get("properties", {})
        result = {}

        for key, value in obj.items():
            if key in props:
                result[key] = self._cast_value(value, props[key])
            else:
                result[key] = value

        return result

    def _cast_value(self, val: Any, schema: Dict[str, Any]) -> Any:
        """根据 Schema 转换单个值。"""
        target_type = schema.get("type")

        # 处理布尔值
        if target_type == "boolean" and isinstance(val, bool):
            return val
        # 处理整数 (排除布尔值，因为 bool 是 int 的子类)
        if target_type == "integer" and isinstance(val, int) and not isinstance(val, bool):
            return val
        # 处理其他直接匹配的类型
        if target_type in self._TYPE_MAP and target_type not in ("boolean", "integer", "array", "object"):
            expected = self._TYPE_MAP[target_type]
            if isinstance(val, expected):
                return val

        # 尝试转换字符串为整数
        if target_type == "integer" and isinstance(val, str):
            try:
                return int(val)
            except ValueError:
                return val

        # 尝试转换字符串为数字
        if target_type == "number" and isinstance(val, str):
            try:
                return float(val)
            except ValueError:
                return val

        # 转换为字符串
        if target_type == "string":
            return val if val is None else str(val)

        # 尝试转换字符串为布尔值
        if target_type == "boolean" and isinstance(val, str):
            val_lower = val.lower()
            if val_lower in ("true", "1", "yes"):
                return True
            if val_lower in ("false", "0", "no"):
                return False
            return val

        # 递归处理数组
        if target_type == "array" and isinstance(val, list):
            item_schema = schema.get("items")
            return [self._cast_value(item, item_schema) for item in val] if item_schema else val

        # 递归处理对象
        if target_type == "object" and isinstance(val, dict):
            return self._cast_object(val, schema)

        return val

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """
        根据 JSON Schema 验证工具参数。

        Args:
            params (Dict[str, Any]): 待验证的参数字典。

        Returns:
            List[str]: 错误信息列表。如果为空，表示验证通过。
        """
        if not isinstance(params, dict):
            return [f"parameters must be an object, got {type(params).__name__}"]
        schema = self.parameters or {}
        if schema.get("type", "object") != "object":
            raise ValueError(f"Schema must be object type, got {schema.get('type')!r}")
        return self._validate(params, {**schema, "type": "object"}, "")

    def _validate(self, val: Any, schema: Dict[str, Any], path: str) -> List[str]:
        """递归验证值的具体实现。"""
        t, label = schema.get("type"), path or "parameter"

        # 类型检查
        if t == "integer" and (not isinstance(val, int) or isinstance(val, bool)):
            return [f"{label} should be integer"]
        if t == "number" and (
            not isinstance(val, self._TYPE_MAP[t]) or isinstance(val, bool)
        ):
            return [f"{label} should be number"]
        if t in self._TYPE_MAP and t not in ("integer", "number") and not isinstance(val, self._TYPE_MAP[t]):
            return [f"{label} should be {t}"]

        errors = []
        # 枚举检查
        if "enum" in schema and val not in schema["enum"]:
            errors.append(f"{label} must be one of {schema['enum']}")

        # 数值范围检查
        if t in ("integer", "number"):
            if "minimum" in schema and val < schema["minimum"]:
                errors.append(f"{label} must be >= {schema['minimum']}")
            if "maximum" in schema and val > schema["maximum"]:
                errors.append(f"{label} must be <= {schema['maximum']}")

        # 字符串长度检查
        if t == "string":
            if "minLength" in schema and len(val) < schema["minLength"]:
                errors.append(f"{label} must be at least {schema['minLength']} chars")
            if "maxLength" in schema and len(val) > schema["maxLength"]:
                errors.append(f"{label} must be at most {schema['maxLength']} chars")

        # 对象属性检查
        if t == "object":
            props = schema.get("properties", {})
            for k in schema.get("required", []):
                if k not in val:
                    errors.append(f"missing required {path + '.' + k if path else k}")
            for k, v in val.items():
                if k in props:
                    errors.extend(self._validate(v, props[k], path + "." + k if path else k))

        # 数组元素检查
        if t == "array" and "items" in schema:
            for i, item in enumerate(val):
                errors.extend(
                    self._validate(item, schema["items"], f"{path}[{i}]" if path else f"[{i}]")
                )
        return errors

    def to_schema(self) -> Dict[str, Any]:
        """
        将工具转换为 OpenAI Function Calling Schema 格式。

        Returns:
            Dict[str, Any]: 符合 OpenAI API 要求的工具定义。
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
