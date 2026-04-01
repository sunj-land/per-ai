# perAll Agents 服务总体架构说明书

## 1. 系统概述
Agents 服务是 perAll 项目中的核心 AI 能力基座，负责提供各类智能 Agent 的执行环境、大模型(LLM)接口封装、多 Agent 工作流编排以及标准化的 RESTful API 服务。

## 2. 目录拓扑与模块边界
```text
agents/
├── api/             # 包装接口层：暴露 FastAPI 路由，负责 HTTP 协议转换和 DTO 校验
├── config/          # 配置中心：包含 agent_config.yaml 等全局配置项
├── core/            # 核心基座：定义 Agent 抽象、生命周期、监控埋点、基础协议
│   └── tools/       # 基础工具封装（如文件系统、注册表等）
├── entries/         # 服务入口：各种 Agent 的实例化工厂与注册入口
├── graph/           # 编排引擎：基于 LangGraph 的图状态机与工作流运行时定义
├── instances/       # 业务实现：具体的业务 Agent 实现（如文章、数据、工作流 Agent）
├── nodes/           # 流程节点：细粒度的 LLM 任务节点（如文本分类、总结）
├── providers/       # 适配器层：不同 LLM 厂商（Azure, OpenAI, LiteLLM 等）的驱动适配
├── service_client/  # 内部通信：与其他微服务（如后端 Backend）交互的 SDK 客户端
└── tests/           # 质量保障：单元测试、集成测试、压力测试
```

## 3. 接口总览
Agents 服务默认通过 FastAPI 监听 `8001` 端口，核心接口如下：

| 接口路径 | 方法 | 职责说明 | 鉴权方式 |
|---|---|---|---|
| `/v1/chat/completions` | POST | 核心对话补全接口，支持流式 NDJSON 返回 (对齐 OpenAI 规范) | API Key |
| `/v1/agent/invoke` | POST | 单次触发指定 Agent 执行具体任务 | API Key |
| `/v1/agent/status` | GET | 获取指定 Agent 当前的状态与可用技能 | 无 |
| `/health` | GET | 存活探针，用于 K8s/Docker 的健康检查 | 无 |

## 4. 技术栈版本
- **语言/运行时**: Python 3.10+
- **Web 框架**: FastAPI + Uvicorn
- **模型路由/网关**: LiteLLM (用于统一多厂商 API 格式)
- **工作流引擎**: LangGraph (langgraph.json)
- **依赖管理**: Poetry (通过 `pyproject.toml` 和 `poetry.lock` 锁定)
- **代码规范**: Flake8 + Black + MyPy

## 5. CI/CD 门禁规则
- **代码门禁 (Linting)**: 提交前强制进行 Flake8 语法检查及 Black 格式化检查。
- **类型检查 (Type Hinting)**: 强制使用 MyPy 进行静态类型推断，无通过禁止合入主分支。
- **测试覆盖率**: 核心模块 (`core/`, `graph/`, `api/`) 单元测试覆盖率必须 >= **80%**。
- **性能基准**: 
  - 静态响应 API P99 延迟 < 50ms。
  - 模型路由分发开销 < 20ms。

## 6. 代码质量评估与建议
### 可维护性评分: **82/100**
*评分依据: 目录结构清晰，职责分离较好；核心层实现了抽象。但部分业务实例(instances)与核心框架(core)存在轻微耦合，部分旧版本 API 测试文件命名需统一规范。*

### 后续重构建议清单
1. **垃圾代码清理固化**: 将本次清理的 16 个低价值/废弃文件（如部分未使用的 `_entry.py`）的删除行为正式合入主分支，精简代码库。
2. **依赖倒置优化**: `instances/` 目录中目前的具体业务逻辑应通过依赖注入的方式挂载到 Agent 基类，避免 `core/` 直接反向依赖具体的业务模型。
3. **并发安全增强**: `core/agent.py` 中的 `self.status` 状态流转在协程高并发场景下存在数据竞争，建议引入 `asyncio.Lock` 进行锁保护。
4. **统一配置中心**: 当前环境变量散落在 `main.py` 和 `providers` 中，建议引入 `pydantic-settings` 建立强类型的全局配置单例。
5. **记忆系统改造**: `Agent.memory` 当前使用无界 List，在长时对话场景下存在内存泄漏风险，建议改造为支持 Redis 备份或 LRU 淘汰机制的结构。
