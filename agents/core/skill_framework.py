import asyncio
import logging
import time
import hashlib
import json
from typing import Any, Dict, Optional, Type, Callable, Coroutine
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

logger = logging.getLogger(__name__)

class SkillConfig(BaseModel):
    """Skill 配置规范"""
    name: str
    version: str = "1.0.0"
    description: str
    timeout: float = 10.0          # 默认超时时间 10s
    retry_attempts: int = 1        # 默认不重试（尝试1次）
    require_auth: bool = False     # 是否需要鉴权
    required_roles: list[str] = [] # 允许执行的角色

class BaseSkill:
    """标准化的 Skill 基类"""
    config: SkillConfig
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    
    def __init__(self):
        self.is_loaded = False
        
    def load(self):
        """动态加载资源"""
        self.is_loaded = True
        logger.info(f"Skill {self.config.name} loaded.")
        
    def unload(self):
        """动态卸载资源"""
        self.is_loaded = False
        logger.info(f"Skill {self.config.name} unloaded.")
        
    async def _execute(self, params: BaseModel, context: Dict[str, Any]) -> BaseModel:
        """异步执行核心逻辑，子类必须实现"""
        raise NotImplementedError

class SkillRegistry:
    """Skill 注册与发现机制"""
    _skills: Dict[str, BaseSkill] = {}
    
    @classmethod
    def register(cls, skill: BaseSkill):
        if skill.config.name in cls._skills:
            logger.warning(f"Skill '{skill.config.name}' is already registered. Overwriting.")
        if not skill.is_loaded:
            skill.load()
        cls._skills[skill.config.name] = skill
        logger.info(f"Registered skill: {skill.config.name} (v{skill.config.version})")
        
    @classmethod
    def unregister(cls, name: str):
        if name in cls._skills:
            cls._skills[name].unload()
            del cls._skills[name]
            logger.info(f"Unregistered skill: {name}")
            
    @classmethod
    def get(cls, name: str) -> Optional[BaseSkill]:
        return cls._skills.get(name)
        
    @classmethod
    def list_skills(cls) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "version": skill.config.version,
                "description": skill.config.description,
                "is_loaded": skill.is_loaded
            }
            for name, skill in cls._skills.items()
        }

class SkillError(Exception):
    """统一的 Skill 异常类"""
    def __init__(self, message: str, code: int = 500):
        super().__init__(message)
        self.code = code
        self.message = message

class SkillInvoker:
    """
    统一的 Skill 调用器
    提供接口规范、参数验证、错误处理、性能监控、重试、超时和结果缓存。
    """
    _cache: Dict[str, Any] = {}
    
    @classmethod
    def _generate_cache_key(cls, name: str, params: Dict[str, Any]) -> str:
        param_str = json.dumps(params, sort_keys=True)
        return f"{name}:{hashlib.md5(param_str.encode()).hexdigest()}"

    @classmethod
    def _check_permissions(cls, skill: BaseSkill, context: Dict[str, Any]):
        """基于上下文的权限控制与路由"""
        if skill.config.require_auth and not context.get("is_authenticated"):
            raise SkillError(f"Skill '{skill.config.name}' requires authentication.", 401)
            
        if skill.config.required_roles:
            user_role = context.get("role", "guest")
            if user_role not in skill.config.required_roles:
                raise SkillError(f"Permission denied. Role '{user_role}' cannot execute '{skill.config.name}'.", 403)

    @classmethod
    async def invoke_async(cls, name: str, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None, use_cache: bool = False) -> Dict[str, Any]:
        """异步调用 Skill"""
        skill = SkillRegistry.get(name)
        if not skill:
            raise SkillError(f"Skill '{name}' not found.", 404)
            
        if not skill.is_loaded:
            raise SkillError(f"Skill '{name}' is not loaded.", 503)
            
        context = context or {}
        
        # 1. 权限与路由检查
        cls._check_permissions(skill, context)
            
        # 2. 参数验证
        try:
            validated_params = skill.input_model(**params)
        except ValidationError as e:
            raise SkillError(f"Parameter validation failed for '{name}': {e.errors()}", 400)
            
        # 3. 缓存拦截
        cache_key = cls._generate_cache_key(name, params)
        if use_cache and cache_key in cls._cache:
            logger.info(f"Cache hit for skill '{name}'")
            return cls._cache[cache_key]
            
        # 4. 性能监控与执行 (重试 + 超时)
        start_time = time.time()
        
        # 动态创建带重试的包装函数
        @retry(stop=stop_after_attempt(skill.config.retry_attempts), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
        async def _run_with_retry():
            return await asyncio.wait_for(
                skill._execute(validated_params, context),
                timeout=skill.config.timeout
            )
            
        try:
            result_model = await _run_with_retry()
            
            # 5. 输出验证
            if not isinstance(result_model, skill.output_model):
                raise SkillError(f"Skill '{name}' returned invalid output type.", 500)
                
            res_dict = result_model.model_dump()
            
            # 缓存结果
            if use_cache:
                cls._cache[cache_key] = res_dict
                
            return res_dict
            
        except asyncio.TimeoutError:
            raise SkillError(f"Skill '{name}' execution timed out after {skill.config.timeout}s.", 504)
        except RetryError as e:
            raise SkillError(f"Skill '{name}' execution failed after retries: {e}", 500)
        except SkillError:
            raise
        except Exception as e:
            raise SkillError(f"Skill '{name}' internal error: {str(e)}", 500)
        finally:
            elapsed = time.time() - start_time
            logger.info(f"Skill '{name}' executed in {elapsed:.3f}s. Context: {context}")

    @classmethod
    def invoke_sync(cls, name: str, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None, use_cache: bool = False) -> Dict[str, Any]:
        """同步调用 Skill"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 如果在异步循环中调用同步方法，需使用 asyncio.run_coroutine_threadsafe (不推荐，但为兼容)
            raise RuntimeError("invoke_sync cannot be called inside a running asyncio loop. Use invoke_async instead.")
        else:
            return asyncio.run(cls.invoke_async(name, params, context, use_cache))

    @classmethod
    def clear_cache(cls, name: Optional[str] = None):
        """清理缓存"""
        if name:
            keys_to_delete = [k for k in cls._cache.keys() if k.startswith(f"{name}:")]
            for k in keys_to_delete:
                del cls._cache[k]
        else:
            cls._cache.clear()
