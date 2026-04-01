import os
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv
import litellm

# 导入时自动加载 .env 文件中的环境变量
load_dotenv()

class LLMClient:
    """
    LLM 客户端类 (单例模式)
    提供基于 litellm 的统一 LLM 访问接口。
    """
    _instance = None
    
    def __new__(cls):
        """
        实现单例模式，确保系统中只有一个 LLMClient 实例。
        """
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """
        初始化客户端配置。
        litellm 会自动从环境变量中读取密钥（如 OPENAI_API_KEY, ANTHROPIC_API_KEY 等）。
        """
        # litellm reads keys from environment variables automatically.
        # e.g. OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.
        pass
        
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        统一的聊天补全接口。
        
        Args:
            messages (List[Dict[str, str]]): 消息列表，每个消息包含 role 和 content。
            model (Optional[str]): 模型名称 (默认使用环境变量 LLM_MODEL 或 gpt-3.5-turbo)。
            temperature (Optional[float]): 采样温度。
            max_tokens (Optional[int]): 最大生成 Token 数。
            **kwargs: 其他传递给 litellm 的参数。

        Returns:
            Any: litellm 的响应对象。
        """
        model = model or os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
        # 安全地解析环境变量
        env_temp = os.getenv("LLM_TEMPERATURE")
        default_temp = float(env_temp) if env_temp is not None else 0.7
        temperature = temperature if temperature is not None else default_temp
        
        env_max_tokens = os.getenv("LLM_MAX_TOKENS")
        default_max_tokens = int(env_max_tokens) if env_max_tokens is not None else 1024
        max_tokens = max_tokens if max_tokens is not None else default_max_tokens
        
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response
        except Exception as e:
            # 这里可以添加特定的错误处理或日志记录
            print(f"LLM Chat Completion Error: {e}")
            raise e

    def embedding(
        self,
        input: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        统一的嵌入 (Embedding) 接口。
        
        Args:
            input (Union[str, List[str]]): 输入文本字符串或字符串列表。
            model (Optional[str]): 模型名称。
            **kwargs: 其他传递给 litellm 的参数。

        Returns:
            Any: litellm 的嵌入响应对象。
        """
        model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        try:
            response = litellm.embedding(
                model=model,
                input=input,
                **kwargs
            )
            return response
        except Exception as e:
            print(f"LLM Embedding Error: {e}")
            raise e
            
    def moderation(
        self,
        input: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        统一的内容审查 (Moderation) 接口。
        
        Args:
            input (str): 需要审查的文本内容。
            model (Optional[str]): 审查模型名称。
            **kwargs: 其他传递给 litellm 的参数。

        Returns:
            Any: litellm 的审查响应对象。
        """
        model = model or "text-moderation-latest"
        try:
            response = litellm.moderation(
                model=model,
                input=input,
                **kwargs
            )
            return response
        except Exception as e:
            print(f"LLM Moderation Error: {e}")
            raise e

# 全局单例实例
llm_client = LLMClient()
