# Agent Skill 框架接入指南与接口文档

## 1. 概述
统一的 Skill 调用框架为 Agents 服务提供了标准化的功能扩展机制，支持动态加载/卸载、参数验证、统一错误处理、性能监控、重试策略、超时管理和结果缓存，并且支持基于运行时的权限控制。

## 2. 接口规范与定义

### 2.1 命名规范与版本管理
- **Skill 命名**：使用全小写下划线分割（snake_case），应准确描述行为，例如 `weather_query`, `github_issue_creator`。
- **类命名**：使用大驼峰（PascalCase），后缀固定为 `Skill`，如 `WeatherSkill`。
- **版本管理**：遵循语义化版本控制（Semantic Versioning, `MAJOR.MINOR.PATCH`）。配置中需显式声明 `version`。不兼容变更需升级 `MAJOR` 版本，并可注册为新 Skill（如 `weather_query_v2`）以实现共存与灰度发布。

### 2.2 灰度发布策略
建议通过以下方式实现 Skill 的灰度发布：
1. **多版本共存注册**：注册 `weather_query` (稳定版) 和 `weather_query_beta` (灰度版)。
2. **基于上下文路由**：在 Agent 中，根据请求 `context` 中的 `user_id` 或 `tenant_id`，判断用户是否在灰度名单内，从而动态决定调用哪个名称的 Skill。

### 2.3 性能监控与告警
框架内部在 `SkillInvoker` 中集成了 `logging`，对每次调用输出耗时统计：
- **监控指标**：
  - 成功率与失败率（通过 `SkillError` 的 code 维度聚合）。
  - 调用耗时（P95/P99 延迟）。
  - 缓存命中率（通过 `Cache hit for skill` 日志统计）。
- **告警要求**：建议对接 Prometheus/ELK，当某 Skill 连续触发 500/504 错误（超时或内部异常）超过设定阈值时，触发告警。

## 3. 开发一个自定义 Skill

开发自定义 Skill 需继承 `BaseSkill`，并定义对应的输入输出 `Pydantic` 模型。

```python
import asyncio
from pydantic import BaseModel, Field
from core.skill_framework import BaseSkill, SkillConfig

class WeatherInput(BaseModel):
    city: str = Field(..., description="城市名称")
    days: int = Field(default=1, ge=1, le=7)

class WeatherOutput(BaseModel):
    city: str
    temperature: str

class WeatherSkill(BaseSkill):
    def __init__(self):
        super().__init__()
        # 定义 Skill 的配置元数据
        self.config = SkillConfig(
            name="weather_query",
            version="1.0.0",
            description="获取指定城市的天气",
            timeout=5.0,           # 默认超时 5 秒
            retry_attempts=3,      # 失败后重试 3 次
            require_auth=True,     # 需要鉴权
            required_roles=["admin", "user"] # 需要特定角色
        )
        self.input_model = WeatherInput
        self.output_model = WeatherOutput
        
    async def _execute(self, params: WeatherInput, context: dict) -> WeatherOutput:
        # 核心业务逻辑实现
        # 抛出 ValueError 等常规异常会被封装为 SkillError
        return WeatherOutput(city=params.city, temperature="25°C")
```

## 4. 注册与卸载

```python
from core.skill_framework import SkillRegistry
from skills.weather_skill import WeatherSkill

# 注册 (支持动态执行)
SkillRegistry.register(WeatherSkill())

# 卸载
SkillRegistry.unregister("weather_query")

# 获取所有注册列表
skills_info = SkillRegistry.list_skills()
```

## 5. Agent 集成示例

Agent 无需关心 Skill 的内部实现、重试或缓存逻辑，统一使用 `SkillInvoker` 进行调用。

```python
import asyncio
from core.skill_framework import SkillInvoker, SkillError

async def agent_action(user_request: dict):
    # 模拟运行时上下文（鉴权信息、角色等）
    context = {
        "is_authenticated": True,
        "role": "user",
        "tenant_id": "t_1001"
    }
    
    # 准备调用参数
    params = {
        "city": user_request.get("city", "Beijing"),
        "days": 3
    }
    
    try:
        # 异步调用 (开启结果缓存)
        result = await SkillInvoker.invoke_async(
            name="weather_query",
            params=params,
            context=context,
            use_cache=True
        )
        print(f"Agent got weather: {result['temperature']}")
        return result
        
    except SkillError as e:
        # 处理规范化的 SkillError (包含状态码 e.code 和信息 e.message)
        print(f"Skill invocation failed [{e.code}]: {e.message}")
        if e.code == 401 or e.code == 403:
            return "对不起，您没有权限查询天气。"
        elif e.code == 400:
            return "您提供的参数有误，请检查。"
        elif e.code == 504:
            return "天气服务响应超时，请稍后再试。"
        else:
            return "系统内部错误。"

# 同步调用方式（在非协程环境下使用）
# result = SkillInvoker.invoke_sync("weather_query", params, context=context)
```
