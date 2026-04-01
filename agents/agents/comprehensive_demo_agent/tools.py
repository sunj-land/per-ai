import os
from typing import Dict, Any
from langchain_core.tools import tool

@tool
def calculator(expression: str) -> str:
    """
    计算数学表达式的值。支持基础的四则运算。
    :param expression: 要计算的数学表达式，如 "2 + 2 * 3"
    """
    try:
        allowed_chars = "0123456789+-*/(). "
        if not all(c in allowed_chars for c in expression):
            return "错误: 表达式包含非法字符。"

        result = eval(expression, {"__builtins__": {}}, {})
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算失败: {str(e)}"

@tool
def web_search(query: str) -> str:
    """
    在网络上搜索信息。
    :param query: 搜索关键词
    """
    mock_db = {
        "langgraph": "LangGraph 是一个用于构建状态代理和多代理应用的库，基于图结构。",
        "deepseek": "DeepSeek 是一家人工智能公司，提供强大的开源和闭源大语言模型。",
        "天气": "今天天气晴朗，气温 25°C，适合出行。"
    }

    for key, value in mock_db.items():
        if key.lower() in query.lower():
            return f"搜索结果: {value}"

    return f"搜索 '{query}' 未找到具体结果。请尝试其他关键词。"

@tool
def file_operation(action: str, filename: str, content: str = "") -> str:
    """
    执行文件操作，如读取或写入文件。
    :param action: 操作类型，"read" 或 "write"
    :param filename: 文件名
    :param content: 如果是写入操作，提供要写入的内容
    """
    try:
        # 获取当前 agents 目录的绝对路径
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        safe_dir = os.path.join(base_dir, "workspace")
        os.makedirs(safe_dir, exist_ok=True)
        safe_path = os.path.join(safe_dir, os.path.basename(filename))

        if action == "write":
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"成功将内容写入文件: {safe_path}"
        elif action == "read":
            if not os.path.exists(safe_path):
                return f"文件不存在: {safe_path}"
            with open(safe_path, "r", encoding="utf-8") as f:
                data = f.read()
            return f"文件 {safe_path} 的内容: {data}"
        else:
            return f"未知操作类型: {action}"
    except Exception as e:
        return f"文件操作失败: {str(e)}"

TOOLS = [calculator, web_search, file_operation]
